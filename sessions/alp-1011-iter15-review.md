---
title: ALP-1011 Iteration 15 Code Review
type: sessions
tags: [review, echoecho, haptics, accessibility, expo-router]
summary: Fixed import ordering in useHapticEngine.ts and redundant VoiceOver label in EmergencyOverlay. All checks pass.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed 10 commits across iteration 15 of the ALP-1011 multi-perspective code review sweep. Changes covered haptic pattern replacement (phantom npm package removal), Expo Router navigate layout fix, hapticPatternPlayer ownership guard, EAS build channel config, deprecated Android permissions removal, accessible emergency overlay, iOS location permissions, expo-battery dependency, and a SectionList type fix.

## Issues Found and Fixed

1. **Import ordering violation** (`apps/student/src/hooks/useHapticEngine.ts`): `RecordedEventType` interface was declared between two import groups, placing `import type { NavEvent }` after a non-import statement. This violates `import/first`. Moved the interface below all imports.

2. **Redundant accessibility label** (`apps/student/src/components/EmergencyOverlay.tsx`): `accessibilityLabel="Emergency. Double-tap to activate emergency navigation."` includes interaction instructions that VoiceOver already provides for buttons. Shortened to `"Emergency navigation"` to avoid repeated "double-tap to activate" speech output.

## Patterns Observed

- The `NSLocationAlwaysUsageDescription` key added to student app.json is a legacy iOS 10 key. Expo 52 requires iOS 16+, making it inert. The expo-location plugin at line 50-53 correctly generates `NSLocationAlwaysAndWhenInUseUsageDescription`. Not harmful, but dead config.
- Pre-existing lint warning in `useVoiceAnnotation.ts:196` (missing `state` dependency in useCallback) predates this iteration.

## Open Items

None. All quality checks pass (typecheck, lint, test).
