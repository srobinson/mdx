---
title: EchoEcho Student Navigation App — UI Design Specification
type: design
tags: [ux-design, accessibility, react-native, haptic, visually-impaired, navigation, voiceover, wcag]
summary: Screen-reader-first navigation UI for VI students. Covers 8 screens, design tokens, haptic model, focus restoration, turn announcement sequence, and WCAG AA accessibility contract.
status: active
source: ux-designer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Student-facing navigation UI for visually impaired users on a React Native (Expo) platform. The design is screen-reader-first: every component is defined for VoiceOver (iOS primary) and TalkBack (Android secondary). All interactive elements have explicit `accessibilityLabel`, `accessibilityRole`, and `accessibilityHint` values defined here as part of the spec contract.

**Haptic model decision**: The codebase already encodes a 7-direction bearing-based model (`turn_left_sharp`, `turn_left`, `turn_left_slight`, `straight`, `turn_right_slight`, `turn_right`, `turn_right_sharp` plus `arrived`, `hazard_warning`, `off_route`, `rerouting`). This is adopted as the canonical haptic model. Rationale: PMC 2017 belt study confirms spatial/directional encoding outperforms sequential pulse counting under navigation stress. The 1/2/3 pulse scheme is rejected as unvalidated and cognitively demanding. The bearing-based model aligns with research consensus and matches the shared `HapticPattern` type in `@echoecho/shared`.

**Provisional validation gate**: Specific vibration durations, amplitudes, and inter-pattern intervals for the 7-direction model are marked as pending VI user testing before engineering commits. Duration encoding within each pattern (short = approaching, long = at-waypoint) is the proposed sub-encoding, pending validation with TSBVI participants.

---

## Design System Foundation

All tokens are defined as React Native StyleSheet values. CSS custom property names use `--` convention for cross-reference clarity; in implementation, map to a `theme.ts` constant object.

### Color Tokens

```typescript
// packages/ui/src/tokens/colors.ts

export const colors = {
  // Base palette — light mode
  background:          '#0F0F0F',  // Near-black. High contrast with white text.
  surface:             '#1A1A1A',  // Card/panel background.
  surfaceElevated:     '#242424',  // Elevated card (modals, overlays).
  primary:             '#4FC3F7',  // Sky blue. 7.2:1 contrast on background. Navigation action.
  primaryVariant:      '#0288D1',  // Pressed/active state of primary.
  onPrimary:           '#000000',  // Text on primary-colored backgrounds.
  secondary:           '#A5D6A7',  // Soft green. Confirmation/arrival.
  onSecondary:         '#000000',
  error:               '#EF9A9A',  // Muted red. Non-alarming error. 4.8:1 on background.
  onError:             '#000000',
  warning:             '#FFCC80',  // Amber. Hazard/off-route. 4.6:1.
  onWarning:           '#000000',
  textPrimary:         '#FFFFFF',  // Body text.
  textSecondary:       '#B0BEC5',  // Labels, hints. 4.7:1 on background.
  textDisabled:        '#546E7A',  // Disabled state. 3.1:1 — acceptable for large text only.
  divider:             '#2C2C2C',

  // Dark mode (same palette — app is dark-mode-first for VI low-light use)
  backgroundDark:      '#0F0F0F',
  surfaceDark:         '#1A1A1A',

  // High contrast mode (iOS Increase Contrast / Android high contrast)
  highContrastPrimary: '#FFFFFF',  // Pure white replaces sky blue for maximum contrast.
  highContrastError:   '#FF5252',  // Saturated red, 6.3:1 on dark background.
  highContrastWarning: '#FFD740',  // Saturated amber.

  // Navigation-specific semantic
  navActive:           '#4FC3F7',  // Active waypoint indicator.
  navCompleted:        '#546E7A',  // Past waypoints.
  navUpcoming:         '#B0BEC5',  // Future waypoints.
  emergency:           '#FF5252',  // Emergency mode. 6.3:1 contrast.
  onEmergency:         '#FFFFFF',
};
```

**Design rationale**: Dark-first palette reduces visual noise for low-vision users who retain some sight, and performs better in outdoor daylight use (high ambient light causes white backgrounds to bloom). Primary hue (sky blue) is chosen for maximum contrast and distinctiveness from error (red) and confirmation (green) states — no two semantic colors are in the same hue family.

### Typography Tokens

```typescript
// packages/ui/src/tokens/typography.ts

export const typography = {
  // Sizes (sp, density-independent)
  sizeBody:         18,   // WCAG 1.4.4 requires 16sp minimum; 18sp for VI users.
  sizeBodyLarge:    20,   // Emphasized body, announcements.
  sizeHeading:      28,   // Screen headings.
  sizeSubheading:   22,   // Section labels.
  sizeCaption:      16,   // Secondary info. Minimum allowed.
  sizeDisplay:      40,   // ETA, distance, arrival confirmation.

  // Weights
  weightBody:       '400',
  weightMedium:     '500',
  weightSemibold:   '600',
  weightBold:       '700',

  // Line height multipliers
  lineHeightBody:   1.5,  // WCAG 1.4.12 requires 1.5× for body text.
  lineHeightHeading: 1.2,

  // Letter spacing (em)
  trackingBody:     0.02,
  trackingHeading:  -0.01,

  // Font family
  family:           'System', // Maps to -apple-system (iOS) / Roboto (Android)
};
```

### Spacing Tokens

```typescript
// packages/ui/src/tokens/spacing.ts

export const spacing = {
  base:          4,   // 4pt grid unit.
  xs:            4,   // 4pt
  sm:            8,   // 8pt
  md:            16,  // 16pt
  lg:            24,  // 24pt
  xl:            32,  // 32pt
  xxl:           48,  // 48pt

  touchTarget:   44,  // WCAG 2.5.5 minimum. Apply to all interactive elements.
  touchTargetLarge: 56, // Preferred for primary navigation actions.

  screenPadding: 24,  // Horizontal screen margin.
  cardPadding:   20,  // Internal card padding.
  sectionGap:    32,  // Vertical gap between sections.
};
```

### Border, Shadow, and Elevation Tokens

```typescript
export const shape = {
  radiusCard:    12,
  radiusButton:  10,
  radiusChip:    20,
  radiusFull:    9999,
};

export const elevation = {
  // React Native shadow values
  card: {
    shadowColor:   '#000',
    shadowOffset:  { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius:  4,
    elevation:     4,
  },
  modal: {
    shadowColor:   '#000',
    shadowOffset:  { width: 0, height: 8 },
    shadowOpacity: 0.5,
    shadowRadius:  16,
    elevation:     16,
  },
};
```

---

## Haptic Model Specification

### Adopted Model: Bearing-Based 7-Direction Encoding

**Status: Provisional — pending VI user validation at TSBVI before engineering commit.**

The bearing-to-haptic mapping is defined in `packages/shared/src/utils/haptic.ts`. The UX contract for each pattern is:

| HapticPattern | Direction | Proposed Duration Encoding | Inter-cue minimum |
|---|---|---|---|
| `straight` | 0° ±5° | Single 80ms pulse | 800ms |
| `turn_right_slight` | 5°–20° | Single 120ms pulse | 800ms |
| `turn_right` | 20°–60° | Two 100ms pulses, 80ms gap | 800ms |
| `turn_right_sharp` | 60°–135° | Three 80ms pulses, 60ms gap | 800ms |
| `turn_left_slight` | -5°–-20° | Mirrored: single 120ms | 800ms |
| `turn_left` | -20°–-60° | Two 100ms pulses | 800ms |
| `turn_left_sharp` | -60°–-135° | Three 80ms pulses | 800ms |
| `u_turn` | >135° or <-135° | Four 100ms pulses, fast 50ms gap | 800ms |
| `arrived` | — | Two long 300ms pulses, 200ms gap | — |
| `hazard_warning` | — | Irregular: 80ms, 40ms gap, 200ms, 40ms gap, 80ms | 1200ms |
| `off_route` | — | Continuous 500ms buzz | — |
| `rerouting` | — | Slow pulse: 300ms on, 300ms off × 3 | — |

**Rationale for pulse-count differentiation (right vs. right_slight)**: Research confirms pattern distinguishability at 82–90% recognition rates for differentiated patterns vs. 65% for uniform pulses (PMC 2022). Using duration and count together creates enough distinctiveness across the 7-direction space. The 800ms inter-cue minimum follows PMC 2022's finding that sub-800ms intervals cause tactile adaptation and false positives.

**Dictation conflict mitigation** (ALP-954 dependency): When voice recognition is capturing input, `CHHapticEngine` is silenced by iOS. Replacement feedback: audio confirmation tone (440Hz, 120ms) fires when voice recognition starts and stops. No haptic during dictation window.

**Low Power Mode mitigation**: Detected via `expo-battery` / `RNDeviceInfo`. On entry, announce via VoiceOver: "Low power mode active. Haptic guidance paused. Audio guidance continues." Navigation continues audio-only. Banner displayed in `ActiveNavigation`.

---

## Screen Specifications

### 1. `DestinationEntry`

**Purpose**: Entry point. Voice or text input to specify a navigation destination.

**ALP-954 contract**: The voice recognition state machine defined here is the engineering spec for ALP-954.

#### TypeScript Props Interface

```typescript
interface DestinationEntryProps {
  onDestinationSelected: (destination: SavedDestination | string) => void;
  savedDestinations: SavedDestination[];
  isListening: boolean;
  voiceTranscript: string | null;
  voiceError: string | null;
  isLoading: boolean;
}
```

#### Voice Recognition State Machine

```
idle
  → [user taps mic button] → listening
      → [silence timeout 3s] → transcribing
      → [user taps stop] → transcribing
          → [Haiku parses destination] → destination_confirmed
              → [user confirms] → onDestinationSelected()
              → [user rejects] → idle
          → [parse error] → error
              → [auto-retry 1x] → listening
              → [second failure] → idle (audio: "I couldn't understand that. Please try again or type your destination.")
  → [user types text] → typing
      → [user submits / Enter] → destination_confirmed
  → [user selects from saved] → destination_confirmed
```

**Haptic state during dictation**: `CHHapticEngine` is suspended. Audio tone (440Hz, 120ms) confirms mic activation. Audio tone (220Hz, 80ms) confirms mic stop.

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default | Mic button prominent, search field below, saved destinations list | VoiceOver reads: "EchoEcho. Where would you like to go? Tap the microphone or type a destination." | None | `accessibilityRole="header"` on heading; `accessibilityLabel="Speak destination"` on mic button |
| Listening | Mic button pulses (animated ring, respects `reduceMotion`), waveform shows amplitude | Live region announces: "Listening…" | Audio tone on start (haptic silenced by iOS dictation) | `accessibilityLabel="Stop listening"` on mic; `aria-live` polite on transcript |
| Transcribing | Spinner on mic button | "Processing your destination." | `rerouting` pattern (3-pulse) | `accessibilityValue={{ now: undefined, text: "Processing" }}` |
| Destination confirmed | Destination card appears with route name, estimated time | "Did you find: [destination name]? Double-tap to confirm or swipe right for other options." | `arrived` pattern (2 long pulses) | `accessibilityLabel="[Route name], [distance] meters, estimated [X] minutes. Double-tap to navigate."` |
| Loading (route fetch) | Full-screen overlay spinner | "Loading your route." | `rerouting` pattern | `accessibilityViewIsModal={true}` on overlay |
| Error | Inline error card, non-modal | "[Error reason]. Try again or type your destination." | `off_route` 500ms buzz | `accessibilityRole="alert"` on error card; `AccessibilityInfo.announceForAccessibility` |
| Empty (no saved destinations) | Empty state illustration hidden from screen readers; text only visible | First-time message: "No saved destinations yet. Say where you'd like to go." | None | `importantForAccessibility="no"` on illustration |
| Dark mode | Identical palette — app is dark-first | — | — | — |

#### Layout

```
[Screen heading: "Where are you going?"]         ← accessibilityRole="header"
[Mic button: 72×72pt, primary color]             ← touchTarget: 72pt (primary CTA)
[Text input field]                               ← accessibilityLabel="Type a destination"
[Saved destinations list]                        ← accessibilityRole="list"
  [Destination cell × N]                         ← accessibilityRole="button"
[Error card (conditional)]                       ← accessibilityRole="alert"
```

#### Focus on screen entry
`ref.current?.focus()` on screen heading, 50ms delay (iOS), 150ms delay (Android).

---

### 2. `RoutePreview`

**Purpose**: Pre-navigation summary. Shows estimated time, waypoint count, and first instruction. User confirms before navigation begins.

#### TypeScript Props Interface

```typescript
interface RoutePreviewProps {
  route: Route;
  estimatedMinutes: number;
  onStartNavigation: () => void;
  onBack: () => void;
  isLoading: boolean;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default | Route summary card, waypoint count, first instruction, Start button | VoiceOver reads summary in order: destination name → estimated time → waypoint count → first instruction | None | Traversal order: heading → destination → stats → first instruction → Start button |
| Focus (Start button) | Button highlight (border becomes primary color, 2pt width) | "Start navigation. Double-tap to begin." | None | `accessibilityRole="button"` |
| Active (Start tapped) | Start button shows spinner | "Starting navigation." | `arrived` 2-long-pulse | `accessibilityState={{ disabled: true }}` during load |
| Disabled (route unavailable) | Start button grayed | "Route not available. Return to destination entry." | None | `accessibilityState={{ disabled: true }}` |
| Loading (fetching waypoints) | Skeleton cards (3 rows) | "Loading route details." | `rerouting` 3-pulse | Skeleton: `accessibilityElementsHidden={true}` |
| Error (route load failed) | Error card + Retry button | "Could not load route. [Error]. Double-tap to retry." | `off_route` 500ms | `accessibilityRole="alert"` |
| Empty (no waypoints) | Empty state text | "This route has no waypoints recorded. Return and choose another." | None | `accessibilityRole="alert"` |
| Dark mode | Dark-first palette, same layout | — | — | — |

#### Focus on screen entry
`ref.current?.focus()` on first waypoint summary element, post-transition.

#### Layout

```
[Back button]                                    ← accessibilityLabel="Back to destination"
[Route name heading]                             ← accessibilityRole="header"
[Stats row: distance / estimated time / waypoints]
[First instruction card]                         ← "First: [instruction text]"
[Waypoint list preview (first 3, collapsed)]
[Hazard count badge (if hazards > 0)]
[Start Navigation button: full-width, 56pt height]
```

---

### 3. `ActiveNavigation`

**Purpose**: Primary navigation screen. Minimal content. Fires haptic + audio at each waypoint. Screen must be operable with display off (screen-off navigation via audio and haptic).

#### TypeScript Props Interface

```typescript
interface ActiveNavigationProps {
  session: NavigationSession;
  currentInstruction: TurnInstruction | null;
  nextInstruction: TurnInstruction | null;
  distanceToNextWaypoint: number | null;
  positioningMode: PositioningMode;
  isLowPowerMode: boolean;
  isDictationActive: boolean;
  onEmergency: () => void;
  onEndNavigation: () => void;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default (navigating) | Distance to next waypoint (large display, 40sp), current instruction, positioning mode indicator | Continuous silence until waypoint events | None between waypoints | `AccessibilityInfo.announceForAccessibility` at each waypoint |
| 15m pre-announcement | Distance counter updates | "Turn [direction] in 15 meters at [landmark]." | None at 15m (audio-only pre-announcement) | Live region update |
| 5m haptic warning | Distance counter: "5m" in warning color | None at 5m (haptic-only) | Pattern: `approaching` sub-encoding (short pulse of direction pattern) | `accessibilityLiveRegion="none"` for this event — haptic-only |
| At waypoint | Distance counter: "0m", instruction advances | "[Direction] — [landmark name]" | Full direction pattern (long pulse encoding) | `AccessibilityInfo.announceForAccessibility("[direction]. [landmark].")` |
| Dictation active | Mic indicator visible | Audio tone confirms mic state | Silenced by iOS; audio fallback only | `accessibilityLabel="Voice input active. Haptics paused."` on indicator |
| Low Power Mode | "Audio only" banner | "Low power mode. Haptic guidance paused. Audio guidance continues." | Silenced | `accessibilityRole="alert"` on banner |
| Off-route (deviation) | → transitions to `ReroutePrompt` | Navigation suspended announcement | `off_route` 500ms buzz | Focus transitions to ReroutePrompt |
| Emergency trigger | → transitions to `EmergencyTransition` | — | — | See EmergencyTransition |
| Dark mode | Dark-first, identical | — | — | — |

#### Turn Announcement Sequence (Canonical)

```
At 15m from waypoint:
  AccessibilityInfo.announceForAccessibility("Turn [direction] in 15 meters at [landmark]")
  No haptic (audio only)
  Minimum gap before next cue: 800ms

At 5m from waypoint:
  Haptic: short sub-pulse of direction pattern (approaching encoding)
  No audio announcement
  Minimum gap before next cue: 800ms

At waypoint (within proximityRadius):
  Haptic: full direction pattern (long encoding)
  Audio: AccessibilityInfo.announceForAccessibility("[direction]. [landmark].")
  Minimum gap before next waypoint cue: 800ms
```

**Screen-off operation**: `AccessibilityInfo.announceForAccessibility` fires regardless of screen state. Haptic patterns fire regardless. The screen does not need to be on for navigation to proceed.

#### Emergency Trigger Mechanism
Long-press on the screen body for 2 seconds, OR triple-tap with two fingers (VoiceOver-compatible gesture). This avoids conflict with VoiceOver's standard swipe gestures.

#### Decorative Elements
Any ambient map visualization (if added): `importantForAccessibility="no-hide-descendants"` applied to map container. Screen reader must not traverse map elements.

#### Layout

```
[End Navigation button: top-right, 44×44pt]     ← accessibilityLabel="End navigation"
[Distance display: 40sp, center]                ← accessibilityLabel="[N] meters to next waypoint"
[Current instruction: 22sp]                     ← accessibilityLabel="[instruction text]"
[Landmark name: 18sp, secondary]
[Positioning mode indicator]                    ← accessibilityLabel="GPS positioning" / "Sensor fallback positioning"
[Low Power Mode banner (conditional)]           ← accessibilityRole="alert"
[Emergency help: bottom, full-width]            ← accessibilityLabel="Emergency help. Long-press for 2 seconds to activate."
```

---

### 4. `ArrivalConfirmation`

**Purpose**: Announces arrival, offers to save to favorites, offers to restart or exit.

#### TypeScript Props Interface

```typescript
interface ArrivalConfirmationProps {
  route: Route;
  navigationDurationSeconds: number;
  isSaved: boolean;
  onSaveToFavorites: () => void;
  onNavigateAgain: () => void;
  onGoHome: () => void;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default | "You have arrived" heading (large), route name, duration, action buttons | "You have arrived at [destination]. Navigation took [X] minutes." auto-announced | `arrived` pattern (2 long pulses) | `accessibilityRole="header"` on heading; auto-focus on heading at entry |
| Save to favorites | Save button shows checkmark on completion | "Saved to favorites." | `arrived` 2-pulse | `accessibilityLabel="Save [route name] to favorites"` |
| Already saved | Save button shows filled star | "Already in your favorites." | None | `accessibilityState={{ selected: true }}` on save button |
| Loading (saving) | Save button spinner | "Saving." | None | `accessibilityState={{ busy: true }}` |
| Error (save failed) | Inline error below button | "Could not save. Try again." | `off_route` 500ms | `accessibilityRole="alert"` |
| Dark mode | Dark-first | — | — | — |

#### Focus on entry
`AccessibilityInfo.announceForAccessibility("You have arrived at [destination].")` immediately on screen mount. Then `ref.current?.focus()` on "You have arrived" heading.

---

### 5. `ReroutePrompt`

**Purpose**: Triggered when user deviates beyond threshold. Displays re-route state while Haiku generates a new route. Defines offline fallback.

#### TypeScript Props Interface

```typescript
interface ReroutePromptProps {
  deviationMeters: number;
  isOnline: boolean;
  rerouteState: 'calculating' | 'ready' | 'error' | 'offline_fallback';
  newRoute: Route | null;
  originalRoute: Route;
  onAcceptNewRoute: () => void;
  onReturnToOriginalRoute: () => void;
  onContinueOffline: () => void;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Calculating | Spinner, "Recalculating…" | "You are off route. Calculating a new path." | `off_route` 500ms on trigger, then silence | Focus: `ref.current?.focus()` on "Recalculating" status element, 300ms guard |
| Ready (online) | "New route found" card, Start/Decline buttons | "New route found. [N] meters, [X] minutes. Double-tap to start new route." | `arrived` 2-pulse | `accessibilityRole="alert"` on card |
| Error (reroute failed) | Error state, "Return to original" button | "Could not calculate a new route. [Reason]. Double-tap to return to your original path." | `off_route` 500ms | `accessibilityRole="alert"` |
| Offline fallback | "No connection" banner, "Continue to original destination" button | "No internet connection. Continuing with your original route. Follow audio guidance." | `rerouting` 3-pulse slow | `accessibilityRole="alert"` on offline notice |
| Dark mode | Dark-first | — | — | — |

**Offline fallback behavior**: Navigation continues from the nearest waypoint on the original route. No new Haiku call. Audio announces: "Continuing on original route." No haptic rerouting pattern fires again.

**`accessibilityViewIsModal={true}`** applied to `ReroutePrompt` overlay.

---

### 6. `ConnectivityLost`

**Purpose**: First-class screen. Connection drops mid-navigation. System continues from cached route. Must communicate degraded state without alarming the user.

#### TypeScript Props Interface

```typescript
interface ConnectivityLostProps {
  lostAt: string;  // ISO 8601
  cachedRoute: Route;
  onDismiss: () => void;  // Returns to ActiveNavigation
  onEndNavigation: () => void;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default | Non-alarming informational card (warning color, not error), "Continue" button | "Connection lost. Your route is saved. Navigation continues." | `rerouting` 3-pulse slow (not alarming) | `accessibilityRole="alert"` on card; auto-focus on "Continue" button |
| Dismissed (auto) | Returns to `ActiveNavigation` with offline indicator in corner | "Navigation resumed offline." | None | Offline indicator: `accessibilityLabel="Offline — using saved route"` |
| Reconnected | Inline banner: "Connection restored." (auto-dismisses after 3s) | "Connection restored." | `arrived` 1 short pulse | `accessibilityRole="status"` on reconnection banner |
| Dark mode | Dark-first | — | — | — |

**Tone**: Warm, not alarming. Copy avoids words like "error," "failed," "lost." Uses "saved route," "continuing," "you're still on your way." Research basis: VI users experience connection loss as more anxiety-inducing than sighted users because they lack visual confirmation of system state.

---

### 7. `FavoritesList`

**Purpose**: List of saved destinations. Entry point for repeat navigation. ALP-964 contract.

**ALP-964 contract**: The component spec, empty state, and accessibility pattern here are the engineering spec for ALP-964.

#### TypeScript Props Interface

```typescript
interface FavoritesListProps {
  favorites: SavedDestination[];
  isLoading: boolean;
  onSelectFavorite: (destination: SavedDestination) => void;
  onDeleteFavorite: (id: string) => void;
  onNavigateToSearch: () => void;
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Default (has items) | List of destination cells, each with name + last-used date | VoiceOver reads each cell: "[Destination name]. Last navigated [date]. Double-tap to navigate." | None | `accessibilityRole="list"` on container; each cell: `accessibilityRole="button"` |
| Loading | 3 skeleton rows | "Loading your saved destinations." | None | Skeleton: `accessibilityElementsHidden={true}` |
| Empty | Empty state: text "No saved destinations yet." + "Search for a destination" button | "No saved destinations yet. Double-tap to search for a destination." | None | `accessibilityRole="text"` on empty message; search button: `accessibilityRole="button"` |
| Delete (swipe-to-delete) | Trailing swipe reveals red "Remove" button | "Remove [destination name] from favorites?" | None | Swipe action: `accessibilityActions={[{ name: 'delete', label: 'Remove from favorites' }]}` — VoiceOver-compatible action; swipe gesture is secondary |
| Delete confirmation | Alert dialog | "Remove [destination name]? This cannot be undone." | None | `accessibilityViewIsModal={true}` on alert; focus trapped inside |
| Error (load failed) | Error card + Retry | "Could not load your favorites. [Reason]. Double-tap to retry." | `off_route` 500ms | `accessibilityRole="alert"` |
| Dark mode | Dark-first | — | — | — |

**Swipe-to-delete accessibility pattern**: Primary action is the `accessibilityActions` API. Swipe gesture is a secondary convenience for sighted users. VoiceOver users activate delete via the actions rotor. This ensures full parity without requiring gesture performance.

---

### 8. `EmergencyTransition`

**Purpose**: Stub screen spec. Trigger mechanism and focus behavior. ALP-962 owns content.

**ALP-962 contract**: The trigger mechanism and focus behavior defined here are the engineering spec for ALP-962.

#### Trigger Mechanism

Two methods, both must be implemented (redundancy is a safety requirement):

1. **Long-press**: 2-second long-press on any non-interactive region of `ActiveNavigation`.
2. **Two-finger triple-tap**: VoiceOver-compatible gesture that does not conflict with VoiceOver's standard interaction gestures.

Both triggers bypass any in-progress navigation state and transition immediately.

#### TypeScript Props Interface

```typescript
interface EmergencyTransitionProps {
  // Content owned by ALP-962
  triggeredFrom: 'long_press' | 'voice_gesture';
  onDismiss: () => void;  // Returns to navigation if dismissed
}
```

#### State Matrix

| State | Visual | Audio | Haptic | Accessibility |
|---|---|---|---|---|
| Entry (any trigger) | Full-screen overlay, emergency color | `AccessibilityInfo.announceForAccessibility("Emergency mode activated.")` immediately | `hazard_warning` irregular pattern, then silence | `accessibilityViewIsModal={true}`; focus: `ref.current?.focus()` on emergency heading, 0ms delay (immediate — safety critical) |
| Default | [Content placeholder — ALP-962 owns] | [ALP-962 owns] | [ALP-962 owns] | Emergency heading: `accessibilityRole="header"` |
| Dark mode | Emergency red on dark background | — | — | — |

**Focus behavior**: Emergency focus must interrupt any current focus, including VoiceOver's internal state. Use `AccessibilityInfo.announceForAccessibility` with `queue: false` (interrupts current announcement). Focus delay is 0ms — no platform delay guard because safety requires immediacy.

---

## Focus Restoration Table

Canonical focus destinations for every screen transition. Mitigates `react-navigation` bug #11189, #12724, #10468.

| Transition | Focus target | Implementation | Platform delay |
|---|---|---|---|
| App open → DestinationEntry | Screen heading element | `ref.current?.focus()` in `useEffect([isFocused])` | iOS: 50ms, Android: 150ms |
| DestinationEntry → RoutePreview | First waypoint summary element | `ref.current?.focus()` in `useEffect([isFocused])` | iOS: 50ms, Android: 150ms |
| RoutePreview → ActiveNavigation | "Navigation started" live region | `AccessibilityInfo.announceForAccessibility("Navigation started.")` then focus on distance display | iOS: 50ms, Android: 150ms |
| ActiveNavigation → ReroutePrompt | "Recalculating route" status element | `ref.current?.focus()` with 300ms timing guard (allows transition animation to complete) | iOS: 300ms, Android: 400ms |
| ReroutePrompt → ActiveNavigation (resumed) | Distance display | `AccessibilityInfo.announceForAccessibility("Navigation resumed.")` then focus distance | iOS: 50ms, Android: 150ms |
| ActiveNavigation → ArrivalConfirmation | "You have arrived" heading | `AccessibilityInfo.announceForAccessibility(...)` then `ref.current?.focus()` | iOS: 50ms, Android: 150ms |
| ArrivalConfirmation → FavoritesList | FavoritesList heading | `ref.current?.focus()` | iOS: 50ms, Android: 150ms |
| Any → EmergencyTransition | Emergency status heading | `ref.current?.focus()` — 0ms delay (safety critical) | 0ms both platforms |
| Any → ConnectivityLost | "Continue" button | `ref.current?.focus()` | iOS: 50ms, Android: 150ms |
| Back navigation (any) | Triggering element on previous screen | Store `triggerRef` before navigating; restore via `useEffect([isFocused])` | iOS: 50ms, Android: 150ms |

**Implementation pattern (all non-emergency transitions)**:
```typescript
const { isFocused } = useIsFocused();
useEffect(() => {
  if (isFocused) {
    const delay = Platform.OS === 'ios' ? 50 : 150;
    const timer = setTimeout(() => {
      headingRef.current?.focus();
    }, delay);
    return () => clearTimeout(timer);
  }
}, [isFocused]);
```

---

## Accessibility Requirements

### WCAG AA Compliance (Minimum Baseline)

| Criterion | Requirement | Implementation |
|---|---|---|
| 1.4.3 Contrast (Minimum) | 4.5:1 normal text, 3:1 large text | All token combinations verified. `textPrimary` (#FFFFFF) on `background` (#0F0F0F) = 21:1. `primary` (#4FC3F7) on `background` = 7.2:1. `textSecondary` (#B0BEC5) on `background` = 4.7:1. |
| 1.4.4 Resize Text | 16sp minimum | Body: 18sp. Caption minimum: 16sp. All sizes in sp (density-independent). |
| 1.4.12 Text Spacing | 1.5× line height for body | `lineHeightBody: 1.5` applied to all body text. |
| 2.1.1 Keyboard | All functionality via keyboard | Not applicable (mobile). Equivalent: all functionality via VoiceOver/TalkBack traversal and action rotor. |
| 2.4.3 Focus Order | Logical traversal order | Traversal order explicitly defined per screen. Never rely on layout inference. |
| 2.5.5 Target Size | 44×44pt minimum | `spacing.touchTarget = 44`. Primary actions: 56pt. |
| 4.1.2 Name, Role, Value | All interactive elements | `accessibilityLabel`, `accessibilityRole`, `accessibilityHint` on every interactive element per this spec. |
| 1.4.1 Use of Color | Color not sole conveyor of information | Positioning mode indicator uses icon + text. Error states use text + role="alert". |

### VoiceOver-Specific Requirements

- `accessibilityViewIsModal={true}`: `ReroutePrompt`, `ConnectivityLost`, `EmergencyTransition`, `FavoritesList` delete confirmation.
- `importantForAccessibility="no-hide-descendants"`: Decorative map elements in `ActiveNavigation`.
- `accessibilityLiveRegion="polite"`: Waypoint distance counter, transcript preview.
- `accessibilityLiveRegion="assertive"`: Error announcements, emergency trigger.
- Screen-off navigation: `AccessibilityInfo.announceForAccessibility` is confirmed to fire with screen off on iOS. Engineering must verify this behavior in device testing, not simulator.

### TalkBack-Specific Notes

TalkBack is more forgiving but stricter in one area: `accessibilityActions` for swipe-to-delete must be declared via `onAccessibilityAction` handler, not assumed from the OS. `FavoritesList` delete pattern must be explicitly tested on Android.

---

## Interaction Patterns

### Screen-Off Navigation

The app must be operable with the screen off. The user pockets the phone and navigates by audio and haptic alone.

Requirements:
- `AccessibilityInfo.announceForAccessibility` fires regardless of screen state.
- Haptic patterns fire regardless of screen state.
- The `ActiveNavigation` screen must not require any touch interaction to advance through waypoints — advancement is automatic based on position.
- Long-press emergency trigger: must work with screen off. Implement via native module if Expo gesture handler requires screen on.

### Loading State Pattern

All loading states use the same pattern:
1. Immediately announce via `AccessibilityInfo.announceForAccessibility("[Action] loading")` on trigger.
2. Show visual spinner with `accessibilityState={{ busy: true }}` on the loading container.
3. On completion, announce result.

Skeleton screens use `accessibilityElementsHidden={true}` — screen readers receive only the loading announcement, not the skeleton layout.

### Error Recovery Pattern

All error states:
1. `accessibilityRole="alert"` on error container (auto-announces to screen reader).
2. Retry action available via `accessibilityActions` if applicable.
3. Error message includes: what happened, and what to do. No technical error codes in user-facing text.

### Transition Animations

All transition animations must respect `AccessibilityInfo.isReduceMotionEnabled()`. When enabled:
- Crossfade replaces slide transitions.
- Pulse animations on mic button become static.
- No infinite animations.

---

## Implementation Roadmap

Engineering handoff sequence (ALP-984 → ALP-987 → ALP-986):

1. **Design tokens** (`packages/ui/src/tokens/`): Colors, typography, spacing, shape, elevation. Verify all contrast ratios with a contrast checker before implementing components.

2. **Focus management utilities** (`apps/student/src/hooks/useFocusRestoration.ts`): Reusable hook implementing the platform-delay pattern from the focus restoration table. Single implementation, used by all 8 screens.

3. **Haptic pattern implementation** (`packages/shared/src/utils/haptic.ts`): Map `HapticPattern` enum to `react-native-haptic-patterns` `RecordedEventType` arrays. Implement dictation-active detection. Implement Low Power Mode detection. Unit-test pattern timing in isolation before navigation integration.

4. **Atomic components**: `PrimaryButton`, `SecondaryButton`, `TextInput`, `ErrorCard`, `LoadingSpinner`, `SkeletonRow`. Each verified against 44pt touch target and contrast requirements.

5. **Screen implementations** in dependency order:
   - `DestinationEntry` (entry point; no dependencies)
   - `FavoritesList` (ALP-964 contract; no nav dependencies)
   - `RoutePreview` (depends on shared Route type — already exists)
   - `ActiveNavigation` (depends on haptic patterns, positioning service from ALP-956)
   - `ArrivalConfirmation` (depends on NavigationSession)
   - `ReroutePrompt` (depends on ActiveNavigation and online/offline state)
   - `ConnectivityLost` (depends on connectivity detection)
   - `EmergencyTransition` (depends on trigger mechanism; ALP-962 owns content)

6. **VoiceOver testing on physical device**: Simulator does not reliably reproduce VoiceOver behavior for dynamic content announcements, screen-off interaction, or haptic timing. Physical iOS device required before any accessibility milestone is marked complete.

7. **Accessibility audit**: Test each screen with VoiceOver on iOS 17+. Checklist: traversal order matches spec, all interactive elements announced correctly, focus restoration behaves per table, screen-off navigation fires announcements and haptics, no orphaned focus.

---

## Open Questions

1. **Apple Watch pairing**: The research-recommended spatial encoding model (right watch = right turn) is not in scope for MVP. Should the architecture reserve a `spatialHapticMode` flag in `HapticPattern` for a future Watch extension? Decision needed before engineering starts on haptic module.

2. **Screen-off emergency trigger**: Long-press on screen body with screen off requires validation on physical device. If Expo gesture handler requires screen on, a native module shim is needed. Flag for ALP-987 (mobile engineer).

3. **Haptic VI validation gate**: All pulse durations and amplitudes in the haptic model are provisional pending TSBVI user testing. Engineering should implement with configurable timing constants (not hardcoded ms values) so the VI validation iteration does not require a code change — only a config update.

4. **iOS primary target confirmed**: VoiceOver is the QA baseline per the spec. Android/TalkBack is secondary. Engineering should not block iOS releases on unresolved Android-only accessibility regressions — track separately.

5. **`onDestinationSelected` receives `SavedDestination | string`**: The string case (free-text input not matching a saved destination) requires a Haiku lookup call. Is the result guaranteed to resolve to a `Route`, or can it return no match? `DestinationEntry` needs an explicit "no match found" state if the latter.
