---
title: EchoEcho Navigator — Full Accessibility & UX Audit
type: research
tags: [ux-research, accessibility, wcag, voiceover, talkback, haptic, student-app, admin-app]
summary: Comprehensive code-level accessibility and UX audit of all student and admin app screens. 23 issues identified across screen reader compatibility, haptic design, contrast, touch targets, and cognitive load.
status: active
source: ux-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

A full read of every user-facing component in `apps/student/`, `apps/admin/`, and `packages/ui/` was completed against the source tree in the `echoecho-worktrees/nancy-ALP-935` worktree. The student app has strong foundational accessibility work (live regions, AccessibilityInfo announcements, focus management on emergency screen, haptic skip announcements) but contains a cluster of meaningful gaps in the navigation screen, keyboard fallback flow, and focus-order logic. The admin app has adequate coverage for a sighted-user tool but carries several usability issues in its complex map interaction flows. The haptic engine is well-implemented; the only open risk is the absence of a documented no-haptics audio fallback guarantee at the engine level.

In total, **23 issues** were identified. 4 are priority 1 (blocking the VI user from completing a core task). 9 are priority 2 (significant gaps). 7 are priority 3 (improvements). 3 are priority 4 (polish).

---

## Detailed Findings

### STUDENT APP — CRITICAL PATH

---

#### ISSUE-01 [P1] NavigateScreen: ProgressCard has no accessible label and progress bar is invisible to screen readers

**File:** `apps/student/app/navigate/[routeId].tsx` — `ProgressCard` component (lines 309–336)

**Finding:** The progress bar is a visual-only element. The containing View has no `accessible` prop, no `accessibilityRole`, and no `accessibilityLabel`. The `Text` nodes inside read "Waypoint X of Y" and the destination — these will be announced separately as individual focusable items with no semantic connection. The progress bar fill (`<View style={progressBarFill}>`) conveys numeric progress with no text equivalent.

**Impact:** A blind user navigating focus to this card hears "Waypoint 3 of 12" and "[destination]" as disconnected items. They cannot determine percent completion. They receive no indication the bar exists.

**Fix:** Wrap the card with `accessible={true}` and a composite `accessibilityLabel` such as `"Progress: waypoint ${current + 1} of ${total} — navigating to ${destination}"`. Mark child elements `accessibilityElementsHidden`.

**WCAG:** 1.1.1 Non-text Content, 1.3.1 Info and Relationships

---

#### ISSUE-02 [P1] NavigateScreen: StatusBar uses color alone to convey navigation state

**File:** `apps/student/app/navigate/[routeId].tsx` — `StatusBar` component (lines 239–272)

**Finding:** Navigation status (navigating, off_route, arrived, searching, emergency) is indicated by a colored dot and a color-coded text label. The dot has no accessible meaning. The `Text` element carries `accessibilityLabel="Navigation status: ${label}${modeLabel}"`, which is correct, but there is no live-region on the status bar itself. If status changes from 'navigating' to 'off_route' while the user's focus is elsewhere, VoiceOver is not proactively notified.

The status bar lacks `accessibilityLiveRegion`. The instruction area (`instructionArea`) has `accessibilityLiveRegion="polite"` but that wraps `InstructionCard`, not the `StatusBar`. Off-route events fire `AccessibilityInfo.announceForAccessibility` in the audio engine, but status changes driven purely from the UI state machine (e.g., GPS acquiring) do not.

**Fix:** Add `accessibilityLiveRegion="polite"` to the `StatusBar` view so that status-label text changes are announced automatically.

**WCAG:** 1.4.1 Use of Color, 4.1.3 Status Messages

---

#### ISSUE-03 [P1] NavigateScreen: InstructionCard arrived state missing accessible grouping

**File:** `apps/student/app/navigate/[routeId].tsx` — `InstructionCard` arrival branch (lines 285–293)

**Finding:** On arrival, the card renders a large checkmark icon and two `Text` nodes ("You have arrived!" and the destination). Neither the icon nor the containing View carries an `accessibilityRole` or composite `accessibilityLabel`. The audio engine announces arrival via `AccessibilityInfo.announceForAccessibility`, but if VoiceOver focus lands on this card independently the user hears two separate focusable text strings with no heading role.

**Fix:**
```tsx
<View
  style={styles.instructionCard}
  accessible
  accessibilityRole="header"
  accessibilityLabel={`Arrived at ${destination}`}
>
  <Ionicons name="checkmark-circle" accessibilityElementsHidden ... />
  <Text accessibilityElementsHidden>You have arrived!</Text>
  <Text accessibilityElementsHidden>{destination}</Text>
</View>
```

**WCAG:** 1.3.1, 4.1.2

---

#### ISSUE-04 [P1] HomeScreen: Keyboard fallback input lacks submit action and accessible role for the search flow

**File:** `apps/student/app/index.tsx` — keyboard fallback section (lines 210–234)

**Finding:** When voice input is unavailable, a `TextInput` appears with `returnKeyType="search"` but no `onSubmitEditing` handler is wired. Pressing the keyboard search button does nothing. A blind user who was directed to keyboard input (via the announcement "Keyboard input opened") has no way to submit the typed destination. The flow is:

1. STT unavailable → user is announced into keyboard mode
2. User types a destination
3. User presses the search key on the keyboard → nothing happens
4. The only submit path is tapping the "Cancel" button, which closes the flow entirely

There is also no search results list connected to the keyboard input; the input is purely a UI scaffold without a routing function.

**Fix:** Wire `onSubmitEditing` to a fuzzy-match lookup against the building index and present results the same way STT disambiguation does. This is a functional gap, not just an accessibility gap.

**WCAG:** 3.3.2 Labels or Instructions, POUR — Operable

---

#### ISSUE-05 [P2] HomeScreen: STT "transcribing" state not announced to screen reader

**File:** `apps/student/app/index.tsx` — voice button (lines 92–125)

**Finding:** When `sttState === 'transcribing'`, the button label changes visually to "Processing..." but no `AccessibilityInfo.announceForAccessibility` fires. The `accessibilityLabel` updates dynamically only when the component re-renders and VoiceOver re-reads it; it does not proactively announce the state change. A user who spoke a destination and released the mic button receives no audible feedback that processing is underway.

**Fix:** In `useSttDestination`, when transitioning to the `transcribing` state, call `AccessibilityInfo.announceForAccessibility('Processing your destination...')`.

**WCAG:** 4.1.3 Status Messages

---

#### ISSUE-06 [P2] HomeScreen: Emergency FAB description says "Triple-tap anywhere" but the gesture conflict exists

**File:** `apps/student/app/index.tsx` — emergency button (lines 281–290), `EmergencyOverlay` (line 20 in overlay)

**Finding:** The emergency FAB's `accessibilityLabel` reads "Emergency. Triple-tap anywhere to activate." However, when VoiceOver is active, single-finger triple-tap is not a standard VoiceOver gesture, so the `TapGestureHandler(numberOfTaps: 3)` in EmergencyOverlay may conflict with VoiceOver gesture interpretation on some iOS versions. The overlay comment acknowledges the two-finger triple-tap as the "in-navigation trigger" but the single-finger tap is claimed compatible. This needs explicit VoiceOver validation. If the gesture does not fire under VoiceOver, blind users have only the FAB — which is overlaid in the bottom-right corner, behind other focusable content, and may be hard to reach via linear focus traversal.

Additionally, the FAB has no `accessibilityHint` mentioning the direct-tap alternative separately from the triple-tap gesture.

**Fix:** Test triple-tap under active VoiceOver on iOS. If it fails, update `accessibilityLabel` to remove the triple-tap instruction and rely solely on the FAB. Add `accessibilityHint="Double tap to open emergency navigation"`.

**WCAG:** 2.5.3 Label in Name, 2.1.1 Keyboard (gesture accessibility)

---

#### ISSUE-07 [P2] NavigateScreen: No audio-only fallback explicitly guaranteed when haptics are suppressed by DND (Android)

**File:** `apps/student/src/hooks/useHapticEngine.ts` (lines 193–198)

**Finding:** On iOS, Low Power Mode is detected and an audio announcement is made when haptics are silenced. On Android, Do Not Disturb (DND) detection is explicitly flagged as TODO with a comment: "Android DND detection requires a native module." When Android DND silences haptics, the `skipCallbackRef` is never called, so the UI-level announcement (`AccessibilityInfo.announceForAccessibility('Haptic feedback unavailable...')`) never fires. The audio engine continues to function, but the user is not informed that their haptic channel is silenced.

**Impact:** A student relying on haptic-first navigation (e.g., with earphones removed) will silently lose haptic signals on Android in DND mode without any warning.

**Fix:** Implement Android DND detection (NotificationManager.getCurrentInterruptionFilter via a native module or a community library) or document this as a known limitation with a user-visible warning in the navigation UI.

**WCAG:** Conformance Note — this is a specific platform gap affecting the primary modality for VI users.

---

#### ISSUE-08 [P2] NavigateScreen: waypointProgress live region not present

**File:** `apps/student/app/navigate/[routeId].tsx` — `progressArea` (lines 215–220)

**Finding:** The `progressArea` View has no `accessibilityLiveRegion`. When `waypointProgress` updates (current waypoint advances), sighted users see the progress bar fill. VoiceOver users receive no automatic notification. The instruction area does announce approaching waypoints via the audio engine, so this is not a blocking gap, but the progress card is a second channel that is completely silent.

**Fix:** Add `accessibilityLiveRegion="polite"` to the `progressArea` View, or wire progress changes to an `AccessibilityInfo.announceForAccessibility` call ("Waypoint ${current + 1} of ${total}").

**WCAG:** 4.1.3 Status Messages

---

#### ISSUE-09 [P2] FavoritesScreen: Loading state has no accessible announcement

**File:** `apps/student/app/favorites.tsx` — loading branch (lines 77–86)

**Finding:** When `isLoading === true`, an `ActivityIndicator` and "Loading your routes..." text are rendered. The `SafeAreaView` has no `accessibilityLiveRegion` and `ActivityIndicator` is not accessible by default (it has no role and its animation is invisible to VoiceOver). No `AccessibilityInfo.announceForAccessibility` fires on mount of the loading state.

**Fix:** Add `accessible={true}` and `accessibilityLabel="Loading your routes"` to the loading container. Optionally add `accessibilityLiveRegion="polite"`.

**WCAG:** 4.1.3 Status Messages

---

#### ISSUE-10 [P2] HomeScreen: `sttConfirmCard` has `accessibilityLiveRegion` but not `accessible={true}`

**File:** `apps/student/app/index.tsx` — STT confirm card (lines 128–152)

**Finding:** The confirmation card (`sttState === 'confirming'`) carries `accessibilityLiveRegion="polite"` on the wrapper View. However, the wrapper is not marked `accessible={true}`, so the live region may not propagate announcements on Android (TalkBack requires the view to be accessible for live regions to function). The card's child Pressable buttons do have correct labels, but the initial announcement of "Navigate to [place]?" depends on the live region working correctly.

**Fix:** Add `accessible={false}` explicitly to the wrapper (to prevent it becoming a focusable group) but verify TalkBack behaviour, OR use `accessibilityLabel` on the parent and `accessible={true}` to group the content.

**WCAG:** 4.1.3, platform-specific TalkBack live-region behavior

---

#### ISSUE-11 [P2] EmergencyScreen: GuideToSafetyButton uses `accessibilityState={{ selected }}` — should be `checked` or `pressed`

**File:** `apps/student/app/emergency.tsx` — `GuideToSafetyButton` (lines 228–262)

**Finding:** When guidance is active, `accessibilityState={{ selected: isGuiding }}` is set on the guide button. The `selected` state is semantically intended for list items and tabs. For a toggle button that activates/deactivates a mode, the correct state is either `{ checked: isGuiding }` (for a checkbox-role element) or the button should change its role and label dynamically. Using `selected` on a `button` role element may be announced incorrectly on iOS ("selected" is read but its meaning in the context of a button is ambiguous to VoiceOver users).

**Fix:** Change to `accessibilityRole="switch"` and `accessibilityState={{ checked: isGuiding }}`, or keep `accessibilityRole="button"` and rely entirely on the dynamic `accessibilityLabel` to convey state.

**WCAG:** 4.1.2 Name, Role, Value

---

#### ISSUE-12 [P3] HomeScreen: `DestinationCard` — chevron icon read by screen reader

**File:** `apps/student/app/index.tsx` — `DestinationCard` (lines 295–339)

**Finding:** The trailing `<Ionicons name="chevron-forward">` inside the main Pressable is not marked `accessibilityElementsHidden`. By default, Ionicons components may expose themselves to the accessibility tree on some React Native versions. If the card is not wrapped with `accessible={true}` to merge its children, VoiceOver may navigate to the chevron separately and announce "chevron-forward image" or similar.

**Fix:** Add `accessibilityElementsHidden={true}` to all decorative Ionicons inside Pressable elements, or ensure the parent Pressable's `accessible={true}` groups all children.

**WCAG:** 1.1.1 Non-text Content

---

#### ISSUE-13 [P3] HomeScreen: `tagline` text has no role and is not grouped with the header

**File:** `apps/student/app/index.tsx` — header section (lines 85–90)

**Finding:** "Where do you want to go?" is the screen's primary instruction but has no accessibility role. It is rendered as plain `<Text>` adjacent to the `accessibilityRole="header"` app name. A screen reader user will encounter "EchoEcho [header]" then "Where do you want to go?" as separate items. This is acceptable but could be improved by grouping them.

**Fix:** Wrap the header in `<View accessible={true} accessibilityLabel="EchoEcho — Where do you want to go?" accessibilityRole="header">` and mark children `accessibilityElementsHidden`.

**WCAG:** 1.3.1

---

#### ISSUE-14 [P3] NavigateScreen: `positioningMode === 'pdr'` icon not announced on transition

**File:** `apps/student/app/navigate/[routeId].tsx` — `handleNavEvent` `position_degraded` case (lines 111–118)

**Finding:** When GPS degrades and PDR activates, the audio engine announces "GPS signal lost. Position estimate may be less accurate." (correct). However, the `StatusBar` renders a `<Ionicons name="cellular-outline">` icon in amber to indicate PDR mode. This icon has no `accessibilityLabel` and is not grouped into the status label's `accessibilityLabel`. If a user asks VoiceOver to read the status bar after GPS degrades, they hear the text label correctly but the icon is invisible or announced as "image".

**Fix:** Add `accessibilityElementsHidden={true}` to the PDR icon (the text label already includes "(estimated position)").

**WCAG:** 1.1.1

---

#### ISSUE-15 [P3] StudentApp root: Loading splash (`authReady === false`) returns null with no accessible feedback

**File:** `apps/student/app/_layout.tsx` (line 35)

**Finding:** While Supabase session is establishing, the root layout renders `null`. The splash screen is visible (via `SplashScreen.preventAutoHideAsync()`), but there is no `AccessibilityInfo.announceForAccessibility` on mount to tell screen reader users that the app is loading.

**Fix:** Add a brief announcement before returning null, or render a minimal accessible loading state rather than null.

**WCAG:** 4.1.3

---

#### ISSUE-16 [P3] FavoritesScreen: Arrow between fromLabel and toLabel is a typographic character

**File:** `apps/student/app/favorites.tsx` — `RouteItem` (line 232)

**Finding:** Routes are displayed as `{fromLabel} → {toLabel}`. The arrow `→` is a Unicode character that may be announced as "right-pointing arrow" or "rightwards arrow" depending on the screen reader. The `accessibilityLabel` on the Pressable correctly reads "from [x] to [y]" — so this is only a problem if the user's focus lands on the `Text` child directly.

The `accessible={false}` on the outer `routeItem` View means children are individually focusable. The inner `routeText` children (`routeName` and `routeBuildings`) are separate focusable Text items. The `routeBuildings` Text reads the raw → character.

**Fix:** Either group the text block with `accessible={true}` and a composite label, or replace the arrow with a plain "to" in the displayed text.

**WCAG:** 1.3.3 Sensory Characteristics

---

### ADMIN APP — USABILITY

---

#### ISSUE-17 [P2] AdminApp: MapView has `accessible={false}` with no keyboard/switch escape hatch documented

**File:** `apps/admin/app/(tabs)/index.tsx` (line 172)

**Finding:** `MapboxGL.MapView` is correctly set `accessible={false}` to prevent the map canvas from entering the accessibility tree. However, all map interactions (placing building vertices, dragging waypoints, marking entrances, pressing route/building features to select them) are gesture-only with no keyboard or switch-control alternative. The admin app is used by sighted O&M specialists, so this is lower severity than student-app issues, but it means the admin UI is completely inaccessible to any O&M specialist who uses switch control or keyboard navigation.

There is no documented accessibility escape hatch (e.g., coordinate input for building polygon, which exists but is buried behind a toolbar button with no announcement).

**Fix:** Document this as a known limitation. Surface the coordinate input escape hatch more prominently in the drawing toolbar. Add `accessibilityHint` to the "Add Building" FAB noting that manual coordinate input is available.

**WCAG:** 2.1.1 Keyboard (exception for map; still a usability issue for some admin users)

---

#### ISSUE-18 [P2] AdminApp: Login screen — error text has no live region or alert role

**File:** `apps/admin/app/(auth)/login.tsx` (lines 58–60)

**Finding:** Authentication errors are rendered as `<Text style={styles.errorText}>{error}</Text>`. There is no `accessibilityLiveRegion`, no `accessibilityRole="alert"`, and no `AccessibilityInfo.announceForAccessibility` call when an error appears. An admin who uses a screen reader (e.g., a low-vision user) signs in, receives an error, and hears nothing.

**Fix:**
```tsx
{error ? (
  <Text
    style={styles.errorText}
    accessibilityRole="alert"
    accessibilityLiveRegion="assertive"
  >
    {error}
  </Text>
) : null}
```

**WCAG:** 4.1.3 Status Messages, 3.3.1 Error Identification

---

#### ISSUE-19 [P2] AdminApp: RecordingBottomBar — stat items have `accessibilityLabel` on Text but parent View is not grouped

**File:** `apps/admin/src/components/RecordingBottomBar.tsx` (lines 83–101)

**Finding:** `statValue` Text elements carry `accessibilityLabel` props (e.g., "Elapsed time: 00:32"). However, the `statItem` View wrapper and the adjacent Ionicons icon are not grouped. This means a screen reader user navigates to: (1) the icon (no label), (2) the time text (has label). The icon press target is tiny and the layout is designed for sighted scanability, not linear screen reader traversal.

Additionally, the stats bar is only visible "after recording starts" but there is no announcement when it appears.

**Fix:** Wrap each stat item with `accessible={true}` and move the label to the View. Mark the icon `accessibilityElementsHidden`. Announce when recording stats become visible.

**WCAG:** 1.3.1, 2.4.6 Headings and Labels

---

#### ISSUE-20 [P2] AdminApp: BuildingCreateMetadataSheet — `FieldLabel` component uses `accessibilityElementsHidden`

**File:** `apps/admin/src/components/building/BuildingCreateMetadataSheet.tsx` (lines 166–172)

**Finding:** The `FieldLabel` helper renders a `<Text accessibilityElementsHidden>` for every form field label. This means the visual field labels (e.g., "Building name *", "Short name", "Category") are **hidden from the accessibility tree**. The individual `TextInput` elements have `accessibilityLabel` props, which is correct, but the form structure (which label belongs to which input) is not conveyed via `accessibilityLabelledBy` or grouping. The `accessibilityElementsHidden` on labels is an over-aggressive suppression.

**Fix:** Remove `accessibilityElementsHidden` from `FieldLabel`. The labels should be in the tree. Use proper label-input pairing via `accessibilityLabelledBy` or ensure input `accessibilityLabel` values match field labels.

**WCAG:** 1.3.1, 3.3.2 Labels or Instructions

---

#### ISSUE-21 [P3] AdminApp: WaypointEditSheet — waypoint type chips use emoji in accessible label

**File:** `apps/admin/src/components/waypoint/WaypointEditSheet.tsx` (lines 31–44, 121–136)

**Finding:** Waypoint type chips include emojis (🟢, 🔴, ↪️, etc.) in the display text. The `accessibilityLabel` correctly reads `"Type: ${t.label}"` without emoji, so this is handled. However, the emoji `Text` node inside the chip (`<Text style={styles.typeEmoji}>{t.emoji}</Text>`) is not marked `accessibilityElementsHidden`. Depending on the React Native version and screen reader, it may be announced as "green circle" or "warning sign" before the label.

**Fix:** Add `accessibilityElementsHidden={true}` to all emoji `Text` nodes in type/category chips throughout the admin UI.

**WCAG:** 1.1.1

---

#### ISSUE-22 [P3] AdminApp: HazardButton missing `accessibilityHint`

**File:** `apps/admin/src/components/HazardButton.tsx` (lines 66–83)

**Finding:** The hazard marking FAB has `accessibilityLabel="Mark hazard at current location"` and `accessibilityRole="button"` but no `accessibilityHint`. An admin user unfamiliar with the workflow has no indication that tapping opens a bottom sheet for selecting a hazard type.

**Fix:** Add `accessibilityHint="Double tap to open hazard type selector"`.

**WCAG:** 3.3.2 Labels or Instructions

---

#### ISSUE-23 [P4] AdminApp: Tab bar icons lack accessible focus indicator differentiation

**File:** `apps/admin/app/(tabs)/_layout.tsx` — `TabIcon` component (lines 9–23)

**Finding:** Tab icons switch between filled and outline variants based on `focused` state. This is a color + icon-shape indicator. The tab bar inherits Expo Router's default `accessibilityRole="tab"` and `accessibilityState={{ selected: focused }}` on each tab item, which is correct. However, the `TabIcon` component renders a raw `Ionicons` with no `accessibilityLabel`. Expo Router adds the tab title as the accessible label, so this is likely fine in practice, but should be verified: the icon label should not conflict with or suppress the tab title label.

**Fix:** Verify with VoiceOver that tab labels are announced correctly. Add `accessibilityElementsHidden={true}` to each `TabIcon` to ensure the icon does not contribute a separate announcement.

**WCAG:** 4.1.2

---

### HAPTIC DESIGN

---

#### HAPTIC-01 [P2] No documented audio fallback contract for haptic engine

The haptic engine (`useHapticEngine`) correctly handles iOS Low Power Mode by notifying the UI layer via `skipCallbackRef`. The navigation screen correctly announces haptic unavailability. However:

1. The audio engine does not explicitly re-announce turn instructions when haptics are skipped — it relies on the pre-queued audio announcement being sufficient.
2. On Android, DND silences haptics silently (see ISSUE-07).
3. There is no test or assertion confirming that the audio priority queue produces an announcement for every event where haptics are also fired.

Recommendation: Add an explicit contract (code comment + unit test) that for every `NavEvent` type that produces a haptic, the audio engine also produces an announcement. This is currently true by inspection but not enforced.

---

### COLOR & CONTRAST

---

#### CONTRAST-01 [P3] GpsAccuracyIndicator uses color alone for accuracy level

**File:** `apps/admin/src/components/GpsAccuracyIndicator.tsx`

The indicator color changes from green (<5m) to orange (<15m) to red (≥15m). The `accessibilityLabel` correctly reads the numeric value ("GPS accuracy: 12 meters"), so the screen reader is covered. However, a low-vision admin user who does not use a screen reader but has red-green color deficiency cannot distinguish green from orange accuracy states. The numeric text resolves this only if it is legible, but at 12px (`fontSize: 12`) it may fall below minimum size for many low-vision users.

**Fix:** Increase `fontSize` to at least 14. Consider adding a text qualifier ("good", "fair", "poor") alongside the numeric value.

**WCAG:** 1.4.1 Use of Color, 1.4.4 Resize Text

---

#### CONTRAST-02 [P4] Login screen subtitle and link text may fail AA contrast

**File:** `apps/admin/app/(auth)/login.tsx`

- `subtitle` text: `#888` on `#1a1a2e` background. Estimated contrast ratio: ~3.5:1. Required: 4.5:1 for AA normal text.
- `linkText`: `#5b5bff` on `#1a1a2e`. Estimated contrast ratio: ~4.1:1. Close to threshold but may fail in dark environments.
- `errorText`: `#ff6b6b` on `#1a1a2e`. Passes (>4.5:1).

**Fix:** Increase subtitle to at least `#aaaacc` on this background, and verify link text meets 4.5:1.

**WCAG:** 1.4.3 Contrast (Minimum)

---

## Recommendations (Prioritized)

### Priority 1 — Block ship

1. **Fix keyboard fallback submit action** (ISSUE-04). Without this, the only input path for users without voice fails silently.
2. **Fix ProgressCard accessibility** (ISSUE-01). Progress is a core navigation indicator with no screen reader exposure.
3. **Fix StatusBar live region** (ISSUE-02). State changes (GPS searching, off route) must be announced without user action.
4. **Fix InstructionCard arrived grouping** (ISSUE-03). The most important navigation event needs proper screen reader delivery.

### Priority 2 — Before first VI user pilot

5. Announce STT transcribing state (ISSUE-05)
6. Validate triple-tap under VoiceOver (ISSUE-06)
7. Implement or document Android DND haptic fallback (ISSUE-07)
8. Add ProgressCard live region (ISSUE-08)
9. Fix loading state announcement in FavoritesScreen (ISSUE-09)
10. Verify TalkBack live region on sttConfirmCard (ISSUE-10)
11. Fix GuideToSafetyButton accessibilityState semantics (ISSUE-11)
12. Fix admin login error live region (ISSUE-18)
13. Fix BuildingCreateMetadataSheet FieldLabel accessibility suppression (ISSUE-20)

### Priority 3 — Improvement sprint

14. Hide decorative icons from accessibility tree throughout (ISSUE-12, ISSUE-14, ISSUE-21)
15. Fix route arrow character (ISSUE-16)
16. Fix admin stats bar grouping (ISSUE-19)
17. Fix GPS accuracy indicator minimum font size (CONTRAST-01)
18. Add haptic/audio fallback contract (HAPTIC-01)
19. Admin map — document accessibility escape hatch (ISSUE-17)

### Priority 4 — Polish

20. Fix tagline grouping with header (ISSUE-13)
21. Announce app loading state (ISSUE-15)
22. Fix tab icon accessibility (ISSUE-23)
23. Fix login contrast ratios (CONTRAST-02)

---

## Sources Consulted

- `apps/student/app/index.tsx` — HomeScreen
- `apps/student/app/navigate/[routeId].tsx` — NavigateScreen
- `apps/student/app/emergency.tsx` — EmergencyScreen
- `apps/student/app/favorites.tsx` — FavoritesScreen
- `apps/student/app/_layout.tsx` — Root layout
- `apps/student/src/components/EmergencyOverlay.tsx`
- `apps/student/src/hooks/useHapticEngine.ts`
- `apps/student/src/hooks/useAudioEngine.ts`
- `apps/student/src/hooks/useOffRouteDetection.ts`
- `apps/admin/app/(tabs)/index.tsx` — Map screen
- `apps/admin/app/(tabs)/_layout.tsx` — Tab layout
- `apps/admin/app/(auth)/login.tsx` — Login screen
- `apps/admin/app/record.tsx` — Recording screen
- `apps/admin/app/save-route.tsx` — Save route screen
- `apps/admin/app/haptic-lab.tsx` — Haptic lab
- `apps/admin/src/components/RecordingBottomBar.tsx`
- `apps/admin/src/components/GpsAccuracyIndicator.tsx`
- `apps/admin/src/components/MapLayerControl.tsx`
- `apps/admin/src/components/HazardButton.tsx`
- `apps/admin/src/components/VoiceAnnotationSheet.tsx`
- `apps/admin/src/components/building/BuildingCreateMetadataSheet.tsx`
- `apps/admin/src/components/building/BuildingDrawToolbar.tsx`
- `apps/admin/src/components/waypoint/WaypointEditSheet.tsx`
- `apps/admin/src/components/waypoint/WaypointEditToolbar.tsx`
- `apps/admin/src/components/CampusGateScreen.tsx`
- `packages/ui/src/HazardPickerSheet.tsx`
- WCAG 2.1 (AA) guidelines throughout
- Previous research: `~/.mdx/research/haptic-user-study-results.md`

## Open Questions

1. Does single-finger triple-tap fire correctly under active VoiceOver on iOS 17/18? Requires device testing.
2. Does Android TalkBack `accessibilityLiveRegion` on non-accessible Views propagate announcements? Requires device testing.
3. Are the haptic patterns distinguishable under real-world dual-task conditions (walking + VoiceOver speech)? Refer to ALP-975 study results.
4. What is the announced text for the `→` arrow character on VoiceOver/TalkBack across OS versions?
5. Is the `accessibilityLabelledBy` prop needed for React Native form associations, or does `accessibilityLabel` on the input suffice?
