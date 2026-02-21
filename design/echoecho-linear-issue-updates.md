---
title: EchoEcho Navigator — Linear Issue Updates (ALP-961, ALP-969)
type: design
tags: [ux-design, echoecho, linear, issue-updates, accessibility, vi-navigation]
summary: Complete updated descriptions for ALP-961 and ALP-969 ready to apply via Linear. Linear MCP unavailable at time of authoring.
status: active
source: ux-designer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

# Linear Issue Updates — Ready to Apply

Linear MCP server (`mcp.linear.app/mcp`) was not loaded in the authoring session.
Apply these via Linear UI or a session where the MCP server is active.

Use `update_issue(id, description)` for each block below.

---

## ALP-961 — Updated Description

```
## Context

Student-facing navigation UI for VI users. Screen-reader-first. React Native (Expo). Consumes pre-generated route data from Claude Haiku (stored locally before navigation begins). Haptic output via `react-native-haptic-patterns`.

**Persona:** VI student navigating an unfamiliar campus building or outdoor path independently.

---

## Screen Inventory

Agent must produce specs for all screens below. Each screen requires all 8 states: default, focus, active, disabled, loading, error, empty, dark mode.

| Screen | Description |
|---|---|
| `DestinationEntry` | Voice or text input to specify a destination. Entry point for navigation. |
| `RoutePreview` | Summarizes the pre-generated route before the user starts walking. Shows estimated time, waypoint count, and first instruction. |
| `ActiveNavigation` | Primary navigation screen. Minimal content. Fires haptic + audio at each waypoint. |
| `ArrivalConfirmation` | Announces arrival, offers to save to favorites, offers to restart or exit. |
| `ReroutePrompt` | Triggered when user deviates beyond threshold. Displays re-route state while Haiku generates a new route. Requires connectivity; defines fallback if offline. |
| `ConnectivityLost` | Displayed when connection drops mid-navigation. System continues from cached route. Must communicate degraded state without alarming the user. |
| `FavoritesList` | List of saved destinations. Entry point for repeat navigation. Includes empty state. (Stub for ALP-964.) |
| `EmergencyTransition` | Stub screen spec defining trigger mechanism and focus behavior when emergency mode activates. ALP-962 owns content. |

---

## Interaction Flow

```
App open
  → DestinationEntry (voice or text)
    → [Haiku pre-generates route, stored locally]
    → RoutePreview
      → ActiveNavigation (loop: position check → haptic/audio → step)
        → [deviation detected] → ReroutePrompt → ActiveNavigation
        → [connectivity lost] → ConnectivityLost (continues from cache)
        → [emergency trigger] → EmergencyTransition
        → [destination reached] → ArrivalConfirmation
          → FavoritesList (if user saves)
          → DestinationEntry (restart)
```

---

## Haptic Interaction Model

**Status: UNVALIDATED DESIGN HYPOTHESIS — pending VI user testing.**

The proposed 1/2/3 buzz pulse encoding (1=straight, 2=left, 3=right) has no published validation. Research consistently favors spatial placement over sequential pulse counting (PMC 2017 belt study). Sequential counting introduces cognitive load under navigation stress.

Spec must resolve with one of two approaches:
1. Adopt an alternative with research grounding: duration encoding (short=approaching, long=at-turn), or spatial encoding via paired Apple Watch (right wrist buzz = right turn).
2. Retain 1/2/3 encoding as provisional and mark all haptic specs as pending VI validation gate.

Do not leave the haptic model blank. Choose one and document the rationale.

### Turn Announcement Sequence

At each waypoint, fire cues at three distances:
- **15m:** Audio pre-announcement ("Turn left in 15 meters at the Science Building entrance")
- **5m:** Haptic warning pattern
- **At waypoint:** Haptic direction cue + audio confirmation

Minimum inter-cue interval: 800ms (prevents tactile adaptation per PMC 2022).

### Haptic Conflict States

On iOS, Core Haptics are silenced in two conditions this app will encounter:

- **Dictation active (ALP-954 dependency):** While voice recognition captures input, haptics will not fire. Define replacement feedback: audio tone, visual flash, or paused guidance.
- **Low Power Mode:** Haptics silenced system-wide. Define degraded navigation experience (audio-only). User must be notified of degraded mode.

Both states must appear in the `ActiveNavigation` state matrix.

---

## Focus Management

Every screen transition must have an explicit focus destination. The `react-navigation` library has a documented bug (issues #11189, #12724, #10468): on back-navigation, screen reader focus resets to the first element rather than the triggering element. For a VI user mid-navigation this is a safety concern.

Required deliverable: focus restoration table for every transition in the flow.

| Transition | Focus lands on | Note |
|---|---|---|
| DestinationEntry → RoutePreview | First waypoint summary element | `ref.current.focus()` in `useEffect` post-transition |
| RoutePreview → ActiveNavigation | "Navigation started" live region | `AccessibilityInfo.announceForAccessibility` |
| ActiveNavigation → ReroutePrompt | "Recalculating route" status element | 300ms timing guard |
| ReroutePrompt → ActiveNavigation | Resumed navigation announcement | |
| ActiveNavigation → ArrivalConfirmation | "You have arrived" heading | |
| Any → EmergencyTransition | Emergency status heading | Must interrupt any current focus |
| Back navigation (any) | Triggering element on previous screen | react-navigation bug mitigation required |

Mitigation pattern: `useEffect(() => { ref.current?.focus() }, [isFocused])` with platform delay (iOS: 50ms, Android: 150ms).

---

## Accessibility Requirements

- Touch targets: 44x44pt minimum (WCAG 2.5.5)
- Body text: 16sp minimum (WCAG 1.4.4)
- Color contrast: 4.5:1 normal text, 3:1 large text (WCAG 1.4.3)
- Every interactive element: `accessibilityLabel`, `accessibilityRole`, `accessibilityHint` defined
- Dynamic content: `AccessibilityInfo.announceForAccessibility` for all waypoint events
- Traversal order: explicitly defined per screen — do not rely on visual layout inference
- `accessibilityViewIsModal`: applied to overlays and re-route prompts
- `importantForAccessibility="no-hide-descendants"`: applied to decorative map elements in `ActiveNavigation`
- Primary screen reader: VoiceOver (iOS). TalkBack (Android) is secondary. VoiceOver is stricter; treat it as the QA baseline.

---

## Design System Dependency

Spec must reference shared design tokens from ALP-984. If ALP-984 does not yet exist, flag as a blocker.

Minimum tokens required before component-level specs:
- `--color-background`, `--color-surface`, `--color-primary`, `--color-error`, `--color-on-primary`
- `--color-background-dark`, `--color-surface-dark`
- `--color-high-contrast-primary` (iOS Increase Contrast / Android high contrast)
- `--font-size-body` (min 16sp), `--font-size-heading`, `--font-weight-body`, `--font-weight-heading`
- `--space-base` (4pt grid), `--space-touch-target` (44pt)
- `--radius-card`, `--shadow-elevation-1`

---

## Output

Persists to: `~/.mdx/design/student-nav-ui-specs.md`

Consumed by:
- **ALP-954** (voice input): needs `DestinationEntry` voice recognition state machine and haptic-muted fallback
- **ALP-962** (emergency mode): needs trigger mechanism from `ActiveNavigation` and `EmergencyTransition` focus spec
- **ALP-964** (favorites/history): needs `FavoritesList` component spec, empty state, swipe-to-delete accessibility pattern

---

## Acceptance Criteria

- [ ] All 8 screens specced with all 8 component states
- [ ] Focus restoration table covers every transition; react-navigation mitigation pattern documented
- [ ] Haptic model resolved: alternative adopted with citation, or 1/2/3 retained as provisional with VI validation gate flagged
- [ ] Haptic conflict states (dictation, Low Power Mode) in `ActiveNavigation` state matrix with defined fallbacks
- [ ] `ConnectivityLost` is a first-class screen with defined user-facing behavior and audio-only fallback
- [ ] Every interactive element spec includes `accessibilityLabel`, `accessibilityRole`, `accessibilityHint`
- [ ] Turn announcement sequence defines cue distances (15m, 5m, at-waypoint) and 800ms minimum inter-cue interval
- [ ] `FavoritesList` includes empty state spec (ALP-964 contract fulfilled)
- [ ] `EmergencyTransition` stub defines trigger mechanism and focus destination (ALP-962 contract fulfilled)
- [ ] `DestinationEntry` voice recognition state machine defined (ALP-954 contract fulfilled)
- [ ] Dark mode and high contrast tokens applied to every component
- [ ] All touch targets documented at 44x44pt minimum

---

## Notes

**Blocking dependencies:**
1. **Haptic model validation** — 1/2/3 pulse encoding is unvalidated. Spec can proceed with provisional model but must be marked for VI user testing before engineering commits. Reference: `~/.mdx/research/vi-navigation-technology-landscape.md` §3.
2. **Design system tokens** — ALP-984 must exist before component specs are finalized.
3. **Route data schema** — Agent needs the waypoint data structure (coordinates, proximity radius, announcement text, haptic pattern reference) to spec `ActiveNavigation`. If schema is owned elsewhere, link it before starting.

**Open questions:**
- Is iOS the primary target? Affects which screen reader is primary QA target.
- Is the app screen-off-compatible? (User pockets phone, navigates by audio/haptic.) Affects which events must fire without screen on.
- Does the app support paired Apple Watch for spatial haptic encoding? This is the research-validated alternative to phone-based pulse counting.

**Research references:**
- react-navigation focus bug: #11189, #12724, #10468
- Haptic encoding research: `~/.mdx/research/vi-navigation-technology-landscape.md` §3
- iOS haptic conflicts: `~/.mdx/research/echoecho-technical-feasibility.md` §2
- Offline navigation: `~/.mdx/research/echoecho-technical-feasibility.md` §4, §5
```

---

## ALP-969 — Updated Description

```
## Context

Admin panel feature. Allows a disability services admin to validate a pre-built route by simulating the student experience before publishing it for student use. Desktop web primary; tablet secondary.

**Persona:** Disability services coordinator. Domain expert in campus accessibility; not a developer. Can preview but cannot modify the routing engine. Responsible for approving routes before student exposure.

---

## Screen Inventory

Agent must produce specs for all views below. Each view requires all 8 states: default, focus, active, disabled, loading, error, empty, dark mode.

| View | Description |
|---|---|
| `RouteList` | Paginated list of all routes with status badges (Draft, Simulated, Approved, Deprecated). Entry point. |
| `SimulationPlayer` | Primary simulation view. Animated position on floor map. Playback controls. Waypoint panel. |
| `WaypointDetail` | Drawer/panel showing the selected waypoint's haptic pattern, announcement text, and proximity trigger radius. |
| `HapticPreview` | Visual representation of the haptic pattern (waveform or pulse diagram). Play button fires the pattern on the admin's device if supported. |
| `AnnouncementEditor` | Inline text editor for the waypoint's audio announcement. Triggers re-simulation of that waypoint on save. |
| `RouteErrorPanel` | Displayed when simulation encounters invalid state: missing waypoints, invalid coordinates, deprecated haptic pattern. Lists all errors with severity. |
| `SimulationSummary` | Post-simulation report. Lists all waypoints, statuses, any errors, and Approve / Request Changes actions. |

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
          → [admin resolves or skips] → playing
      → [simulation reaches end] → complete
          → [admin approves] → route status = Approved
          → [admin requests changes] → route status = Draft
  → [admin clicks Step Forward/Back] → at-waypoint (from idle or paused)
```

Unsaved edits: if admin navigates away with unsaved annotation edits, show a confirmation dialog before discarding. Auto-save draft annotation after 2 seconds of inactivity.

---

## Simulation Fidelity Scope

**In scope — what the simulation validates:**
- Haptic pattern fires at correct waypoint proximity threshold
- Audio announcement text is correct and complete
- Waypoint sequence is logically ordered (no backtracking, no gaps >50m)
- All waypoints have assigned haptic patterns and announcement text

**Out of scope — what simulation does not validate:**
- GPS or PDR positioning accuracy on the actual physical route
- Real-time sensor behavior
- Network latency during student navigation

Admin must understand this boundary. The `SimulationPlayer` UI must communicate it (e.g., a persistent "Logical simulation only — field test required before student use" notice).

---

## Route Data Model

The spec must include or reference this TypeScript interface. If a backend issue owns the schema, link it; do not invent a conflicting one.

```typescript
interface Waypoint {
  id: string;
  label: string;                    // human-readable, e.g. "Science Building main entrance"
  coordinates: { lat: number; lng: number };
  proximityRadiusMeters: number;    // haptic/audio triggers when student within this radius
  hapticPatternId: string;          // references pattern library
  announcementText: string;         // full text of audio announcement
  order: number;                    // position in route sequence
}

interface Route {
  id: string;
  name: string;
  campusId: string;
  status: 'draft' | 'simulated' | 'approved' | 'deprecated';
  waypoints: Waypoint[];
  createdBy: string;
  lastSimulatedAt: string | null;   // ISO 8601
  approvedAt: string | null;
  notes: string;
}
```

---

## Multi-Route Management (RouteList)

Admin needs to manage many routes across many buildings. `RouteList` requirements:

- Filter by status (Draft, Simulated, Approved, Deprecated)
- Filter by building / campus area
- Sort by last modified, last simulated, status
- Status badge color must not rely on color alone (add icon or text label — WCAG 1.4.1)
- Bulk actions: Deprecate selected, Export selected as JSON
- Empty state: "No routes yet. Import a route or contact your routing administrator." with a primary action button.

---

## Playback Controls

`SimulationPlayer` playback controls must be keyboard-operable and screen-reader-accessible.

| Control | Action | Keyboard shortcut | ARIA |
|---|---|---|---|
| Play / Pause | Toggle simulation | Space | `role="button"`, `aria-pressed` |
| Step Forward | Advance one waypoint | → | `role="button"` |
| Step Back | Go to previous waypoint | ← | `role="button"` |
| Speed | 1x / 2x / 4x playback | S | `role="listbox"` or segmented control |
| Scrub | Jump to waypoint N | Click waypoint in list | `role="option"` in waypoint list |

Simulation progress: announce current waypoint and total to screen reader on each step change via `aria-live="polite"`.

---

## Accessibility Requirements

Admin panel must meet WCAG AA. Disability services staff may themselves be disabled.

- Touch/click targets: 44x44pt minimum (WCAG 2.5.5)
- Color is never the sole status indicator (WCAG 1.4.1) — status badges use icon + label
- All form fields: visible labels, not placeholder-only (WCAG 1.3.1)
- Keyboard navigation: full tab order through all controls; no keyboard trap except modals
- Modals: `role="dialog"`, `aria-modal="true"`, focus trapped inside, restored on close
- `aria-live` regions for simulation progress and error announcements
- `AnnouncementEditor`: `role="textbox"`, `aria-label`, character count announced via live region
- Error messages: associated to their field via `aria-describedby`

---

## Responsive Behavior

| Breakpoint | Behavior |
|---|---|
| ≥1280px (desktop) | Two-column: map/player left, waypoint detail right |
| 768–1279px (tablet landscape) | Two-column, narrower detail panel |
| <768px (tablet portrait / mobile) | Single column: player full width, detail opens as bottom sheet |

Mobile is not a primary target. If screen width < 480px, show a banner: "Route simulation is optimized for tablet or desktop." Do not block access — degraded layout is acceptable.

---

## Connectivity

Simulation must run from locally cached route data. Do not require live API calls per simulation step. On connectivity loss:
- Simulation continues uninterrupted from cached data.
- A non-blocking banner announces offline mode.
- Save/approve actions queue and fire when connection restores.
- `RouteErrorPanel` distinguishes network errors from data errors.

---

## Output

Persists to: `~/.mdx/design/admin-route-simulation-specs.md`

Consumed by:
- **ALP-990** (Admin Panel frontend): needs complete component specs, state machine, route data model, and responsive breakpoint behavior

---

## Acceptance Criteria

- [ ] All 7 views specced with all 8 component states
- [ ] Simulation session state machine covers: idle, playing, paused, at-waypoint, edit-mode, error, complete
- [ ] Route data model TypeScript interface included in spec or linked to owning issue
- [ ] `RouteList` filter, sort, empty state, and bulk actions specced
- [ ] Playback controls define keyboard shortcuts and ARIA roles for every control
- [ ] Simulation fidelity boundary documented in spec and in `SimulationPlayer` UI (persistent notice)
- [ ] Unsaved-edit behavior defined (auto-save + confirmation on navigate-away)
- [ ] `RouteErrorPanel` covers: missing waypoint, invalid coordinates, deprecated haptic pattern
- [ ] `SimulationSummary` defines Approve and Request Changes actions with their state transitions
- [ ] Admin panel explicitly meets WCAG AA — documented in spec, not assumed
- [ ] Status badges use icon + label, not color alone
- [ ] Responsive breakpoints defined for ≥1280px, 768–1279px, <768px
- [ ] Offline behavior defined: simulation continues from cache, save actions queue

---

## Notes

**Blocking dependencies:**
1. **Route data schema** — If a backend or routing engine issue owns the canonical `Route` / `Waypoint` schema, link it. The TypeScript interface in this spec must match. Do not allow the admin frontend (ALP-990) and the navigation engine to invent independent schemas.
2. **Haptic pattern library** — `WaypointDetail` references `hapticPatternId`. The pattern library must be defined before this view can be fully specced. If it is owned by ALP-961 or a separate engineering issue, link it.
3. **Design system tokens** — Admin panel must reference the same token foundation as ALP-988. If ALP-988 does not exist, flag as a blocker.

**Open questions:**
- Can the admin edit waypoint coordinates, or only annotation (announcement text, haptic pattern)? This determines whether `WaypointDetail` needs a coordinate editor and map drag interaction.
- Is route creation in scope for the admin panel, or only route review and approval? If creation is out of scope, `RouteList` needs a clear "import route" CTA with format specification.
- Is simulation export (PDF or JSON summary) in scope for this issue or deferred?
- Who can approve a route — any admin, or only a specific role? This affects whether the Approve action appears for all admin users.

**Research references:**
- Admin accessibility requirement (staff may be disabled): `~/.mdx/research/echoecho-technical-feasibility.md` §1
- Haptic pattern library reference: `~/.mdx/research/vi-navigation-technology-landscape.md` §3
- NYU Tandon VR pre-testing study (validates simulation as confidence-building tool): `~/.mdx/research/vi-navigation-technology-landscape.md` §5
```
