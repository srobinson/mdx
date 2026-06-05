---
title: Inspect detail fullscreen controls and export trigger
type: sessions
tags: [frontend, transport-matters, exchange-detail, inspect]
summary: Added inspect-tab controls for fullscreen overlay and HTML export launch in ExchangeDetail, plus RTL coverage.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary
Implemented the inspect-only controls requested by the mailbox item in transport-matters `ExchangeDetail`. The tab bar now includes maximize and download buttons when the INSPECT tab is active. Maximizing renders a fullscreen overlay with the live `InspectTab` view and a close control. Download calls the existing `downloadInspectHtml` utility.

## Architecture Decisions
- Kept all behavior in `www/src/components/ExchangeDetail.tsx` so no API or `InspectTab` contracts changed.
- Added a local `fullscreen` boolean state and `useEffect` keydown wiring scoped to the overlay lifecycle.
- Added inline icon components (`ExpandWindowIcon`, `DownloadIcon`, `CloseIcon`) to avoid new dependencies and match the local SVG pattern.
- Moved jump-to-transport handler into a shared callback to ensure overlay closes before tab transition from either live or fullscreen `InspectTab`.
- Added component-level unit test coverage in `www/src/components/ExchangeDetail.test.tsx` for fullscreen open/close and download invocation.

## Performance Notes
- No new render-heavy behavior introduced.
- Overlay is only mounted when requested.
- Keyboard listener is attached only while fullscreen is active and removed on close/unmount, avoiding persistent event-handler overhead.
- Existing `InspectTab` remains unchanged and not forced expanded.

## Deviations from Spec
- None for this item. Existing spec for this task confirmed by review message says no `InspectTab` change.

## Open Items
- If a reviewer requests focus management inside overlay, add explicit focus restoration when opening/closing.
