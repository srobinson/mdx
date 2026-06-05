# CameraTrackControls mount prep

## (a) Pre–Piece Motion mount

- **Born** `c532388d` (`feat(animation): add authored camera tracks`) as `src/panels/CameraTrackControls.tsx`.
- **Mounted** by `src/panels/StripControls.tsx:StripControls` as bare `<CameraTrackControls />` (no props; panel read `editor.openAnimationAssetId` + `editor.transport` itself).
- **Host chain**: `BottomDock` → `StripControls` → `CameraTrackControls`.
- **Cutover** `6403128f` (`feat(motion): Editor Piece Motion workspace binding and cutover (F1) #86`): renames to `src/studio/CameraTrackControls.tsx`, deletes `StripControls`, leaves `BottomDock` hosting only `PieceMotionPanel`. Unmounted since.

## (b) Live candidate mount sites (path:symbol)

1. `src/panels/BottomDock.tsx:BottomDock` — sole dock host; natural sibling under Motion card.
2. `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel` — already owns piece transport UI; can supply `playheadMs`.
3. `src/studios/editor/MotionCapabilitySlots.tsx:MotionDockSlot` — lazy motion FeatureSlot; mount only when motion capability ready.
4. `src/studios/editor/EditorStudio.tsx:EditorApp` / `StudioShell` dock prop — shell-level session host (matches test harness pattern).
5. New Studio session wrapper (as in `tests/studioCameraControls.test.tsx:StudioHarness`) — owns `animationAssetId` state.

## (c) Props / providers

Props: `animationAssetId: string | null`, `onAnimationCreated(id)`, `playheadMs: number`.
Context/store still live under `EditorCommandProvider` in `EditorStudio`: `useEditorCommandDispatch`, `useCameraSnapshotReader` (`core.getState`), `selectAuthoredWorkbench`, `beginHistoryBatch`/`endHistoryBatch`, `useAuthoredScrubGesture`. Session must own open Animation + playhead; store no longer has `openAnimationAssetId`.

## (d) Present-tense docs needing truth updates post-mount

- `ANIMATION.md` — "authoring panel … is not mounted in any production studio"
- `STUDIO.ANIMATION.md` — "written but never mounted in production"
- `INTERACTIVE.md` — "authoring panel is not mounted in any production studio"
- `CAMERA.md` — segment inspector / capture-and-tune described as live product surface; lane ownership claims in STUDIO.ANIMATION.md too

## (e) Rot since unmount

Imports resolve (`selectAuthoredWorkbench`, `getScoreDurationMs`, `../panels/motion/motionOptions`, `useAuthoredScrubGesture`). No since-renamed import breakage observed; component is type-checked in worktree tsc. Main contract change is prop injection vs pre-cutover store self-bind.
