# Camera UX delta: opus-v3 storyboard vs feat/mount-camera-track (749f3a2)

## 1. Today

The dock (`src/panels/BottomDock.tsx:BottomDock`) hosts two stacked sections: the filmstrip
(`src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, cards from
`src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` with Build in, State, transition cards;
transport row with Play/Loop/rate and `TransportPlayhead`; a `Snapshot current scene` button) and the
camera section (`src/studio/CameraTrackControls.tsx:CameraTrackControls`, mounted through
`src/studio/CameraTrackSection.tsx:CameraTrackSection`, session Animation owned by `EditorApp` in
`src/studios/editor/EditorStudio.tsx`). The right rail is `src/panels/motion/MotionInspector.tsx`
(`StateInspector`, `TransitionInspector`, `ArrivalInspector`) behind `MotionInspectorSurface`.
Camera keyframes live at free milliseconds on a session-opened Animation asset.

## 2. Delta table

| Mockup element | Exists today as | Change | Size |
|---|---|---|---|
| Strip of Build in / State / transition cards | `PieceStateStrip` cards | KEEP | - |
| Transport row (Play, Stop, Loop, rate, time, scrub) | `PieceMotionPanel` transport + `TransportPlayhead` | KEEP | - |
| Snapshot placeholder card (`+`) at strip end | `Snapshot current scene` button in panel header | MOVE into strip as trailing card | S |
| Playhead cursor riding across the cards | NONE (scrub bar only) | NEW in `PieceStateStrip` (position from transport time over card layout) | M |
| State card frame: thumbnail rendered from the bound view | `renderThumbnail` via thumbnail capability, fixed axis (`src/thumbnail/thumbnailView.ts:createOrthographicThumbnailView`) | RESTYLE + NEW pose-driven view builder beside `createOrthographicThumbnailView` (perspective + arbitrary `CameraPoseSnapshot`) | L |
| Ghosted dashed frame for inherited (standing) view | NONE | NEW (strip styling + standing-view resolution) | S |
| View ownership tag (solid `V1` / dashed `↪ v3`) | NONE | NEW on State cards | S |
| Azimuth/elevation micro on the tagline | NONE | NEW (derive from bound pose) | S |
| Hover lens button (capture live view onto a card) | NONE | NEW on State cards, reuses the capture op | S |
| Transition camera row in words (`↻ 90° → v2`) | NONE (sweep shown only in `CameraSegmentEditor`) | NEW on transition cards (derived from bound move) | M |
| Boundary cut row (`Cut → v3`) | NONE | NEW (derived: both sides own, no move) | S |
| Hover `+ Camera` affordance on empty transitions | NONE | NEW | S |
| Stage capture button naming the entered state (`Capture view → state 5`) | `CameraTrackControls` `Capture view at X.Xs` button | MOVE to stage overlay; readdress from playhead ms to the entered State | M |
| Stage HUD camera line (`camera 0° / 62° ortho`) | NONE | NEW (read `core.getState`) | S |
| Inspector: Piece motion groups (order/curve/easing/duration) | `TransitionInspector`, `ArrivalInspector` | KEEP | - |
| Inspector: State panel Camera group (owns/inherits, Capture live view here) | NONE | NEW in `StateInspector` | M |
| Inspector: State `Hold` field | NONE (`holdMs` exists only on assembly exit in `src/domain/score.ts`) | NEW or defer (name it out of scope) | S |
| Inspector: Camera view panel (az/el/distance, projection, holds note, Recapture, Remove view) | NONE (no pose fields anywhere; `Remove view` button lives in `CameraTrackControls`) | NEW panel; MOVE `Remove view`; pose decomposition per CAMERA.md channels | L |
| Inspector: Camera move panel (pose path/easing/cut, projection path/easing/cut, sweep, Reverse, ± Full turn, Remove move) | `CameraTrackControls.tsx:CameraSegmentEditor` (all fields exist) | MOVE to `MotionInspector` as a selectable panel | M |
| Inspector: Hard cut panel (explanation + resolve buttons) | NONE | NEW | S |
| Topbar census (`5 states · 3 views · 2 moves`) | NONE | NEW (derived counts) | S |
| — removed by the mock: `Camera track` dock section | `CameraTrackSection` in `BottomDock` | DELETE (dock hosts only the strip) | S |
| — removed: keyframe chip row (`1 · 0.0s`) | `CameraTrackControls` keyframe buttons | DELETE (cards are the keyframes) | S |
| — removed: `Keyframe ms` scrub | `CameraTrackControls` `ScrubField` | DELETE (anchoring replaces free ms) | S |
| — removed: pose/projection toggle + cut rows in dock | `CameraSegmentEditor` rows | MOVE (see Camera move panel) | - |
| — removed: sweep row + orbit buttons in dock | `CameraSegmentEditor` orbit actions | MOVE (same) | - |
| — removed: possession status/legend | never built | - | - |

Counts: KEEP 3 · RESTYLE 1 · MOVE 5 · DELETE 3 · NEW 14.

## 3. Domain delta

Today the track is `src/domain/cameraTrack.ts:CameraTrack` (keyframes at free `atMs`) on an Animation
asset, edited by `src/domain/cameraOperations.ts:applyCameraOperation` (capture / move / remove /
patch-segment / reverse-orbit / full-turn), session-scoped via `EditorApp.cameraAnimationAssetId`.
The mock replaces free time with anchoring: a State owns at most one view, a transition owns at most
one move; inheritance is the standing view (last owning State); both-sides-own with no move is a
boundary cut; a move with no owned endpoints orbits the standing view and returns. That needs:
- An anchored camera lane stored with the attached structure's score (beside its state sequence,
  keyed by `stateId` / transition index), replacing the session Animation for this surface. This is
  the storage decision to confirm with Stuart: camera becomes part of the piece, not a separate asset.
- New document operations (bind-view-to-state, remove-state-view, set/patch/remove-transition-move)
  superseding the free-ms trio; `patch-camera-segment`, orbit reverse and full-turn carry over onto
  the move. All flow through the existing `dispatchAuthoredEdit` path.
- A pure compiler: anchored lane + transport layout (`src/domain:getStateTransitionSegmentMs`,
  `src/state/transportSelectors.ts:getPieceTransportDurationMs`) → `CameraTrack` keyframes at ms.
  The sampler contract is untouched; boundary cuts compile to cut segments at the boundary fraction.
- Producer rebind: `src/studios/editor/useCameraTrackFrame.ts` reads the compiled track from the
  attached piece instead of `findAnimationAsset(session id)`.

## 4. Untouched

`src/evaluation/cameraTrackSampleAt.ts` and its deferred chunk/port; the possession seam
(`src/camera/cameraTrackAuthority.ts`, `cameraTrackFrame.ts`, `cameraFrameWriter.ts`,
`CameraDriver.tsx`) including detach/rearm/release semantics; the transport clock and score-governed
duration; `TransportFrameDriver` and the staged-scene pipeline; persistence machinery (new ops ride
the same authored-edit and IndexedDB path); the budget architecture (chunks re-measured, not
reshaped); piece motion editing itself (order/curve/easing/duration fields and their ops).

## 5. Slice sketch

1. **Anchored camera domain + compiler.** Anchored lane types, ownership/inheritance resolution, new
   ops, compile-to-`CameraTrack` with unit tests. Files: `src/domain/cameraTrack.ts` (or a new
   `cameraStoryboard.ts`), `src/domain/cameraOperations.ts`, `tests/cameraOperations.test.ts`.
2. **Producer rebind + capture-to-state.** Stage capture button (names the entered State), lens
   hover capture, session Animation removed from `EditorApp`; producer compiles from the piece.
   Files: `src/studios/editor/EditorStudio.tsx`, `useCameraTrackFrame.ts`,
   `src/studio/CameraTrackControls.tsx` (capture path out), `tests/cameraTrackPlayback.test.tsx`.
3. **Inspector ownership.** Camera view / Camera move / Hard cut panels; State and transition camera
   groups; `CameraSegmentEditor` moves in; `CameraTrackSection` leaves `BottomDock`. Files:
   `src/panels/motion/MotionInspector.tsx`, `src/panels/BottomDock.tsx`,
   `src/capabilities/motion/MotionCapability.tsx`, `src/studio/` (section retired).
4. **Storyboard strip.** Ownership tags, camera rows, cut rule, `+ Camera` hover, strip playhead
   cursor, Snapshot as trailing card. Files: `src/panels/motion/PieceStateStrip.tsx`,
   `PieceMotionPanel.tsx`, `src/panels/motion/motion.css`.
5. **View-bound thumbnails.** Pose-driven thumbnail view (NEW beside
   `createOrthographicThumbnailView`), ghosted inherited frames, cache keyed by bound pose. Files:
   `src/thumbnail/thumbnailView.ts`, `thumbnailRenderer.ts`, `thumbnailCache.ts`,
   `src/capabilities/thumbnails/ThumbnailCapability.tsx`.

Feel gate: slices 2 and 4 change what Stuart touches during Play; both need his live drive.
