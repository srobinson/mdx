---
title: Cubicell State display toggle
type: design
tags: [cubicell, motion, state, visibility]
summary: Authored hide on a State, dim adjacent transition cards, play skips with a cut.
status: active
project: cubicell
confidence: high
created: 2026-08-15
updated: 2026-08-15
---

# State display toggle

## Problem

The Motion strip shows every State and the authored Transition between neighbors. Long pieces get hard to read, and a State that should not be in this take still plays. Photoshop's eye is the control people reach for. States are a time sequence, not a z-stack, so the adjacent Transition cards need a rule that does not invent a new gap.

Constraints from the current system: `State` has closed keys. `stateIds` lockstep with keyframes. `transitions.length === N-1`. Delete removes the document. Cube/STRUCT eye is spatial cell visibility and must not be reused as the operation.

## Usage

The author clicks the eye on a State card. The card stays. Both neighboring Transition cards stay and dim. Play and camera skip that State with a zero-duration cut to the next visible neighbor. The hidden State stays selectable so it can still be edited. Undo and reload keep the hide.

```ts
dispatch(createDocumentEditCommand({
  hidden: true,
  id: stateId,
  kind: "set-state-hidden",
}));

const playable = presentableStateTransitionTrack(track, (id) =>
  isStateHidden(findState(workbench, id)),
);
```

Strip mapping keeps index alignment. `states[i]` still pairs with `transitions[i]`. Chrome reads `hidden`. It does not filter.

## Shape

Organizing structure: one derived presentable sequence. Not a session set. Not a second authored track.

```ts
type State = {
  assetId: string;
  id: string;
  name: string;
  pose: PoseRevision;
  hidden?: true;
  view?: StateCameraView;
};

function isStateHidden(state: { hidden?: true } | undefined): boolean;

function presentableStateTransitionTrack(
  track: StateTransitionTrack,
  hidden: (stateId: string) => boolean,
): StateTransitionTrack;

function presentablePieceScore(workbench: Workbench, asset: StructureAsset): PieceScore;
```

`hidden?: true` is omitted when shown. The op carries `hidden: boolean` so it is idempotent.

`presentableStateTransitionTrack` returns the same track reference when nothing is hidden. Otherwise it keeps visible keyframes. Originally adjacent visible pairs keep their authored transition. A new adjacency, where a hidden State used to sit between them, becomes `{ mode: "cut", settings: { ...defaultMorphSettings, durationMs: 0 } }`. If that clock is 0 ms and two or more States remain, `getPieceTransportDurationMs` reports 1 ms so Play still runs.

Callers of the playable clock use the presentable score: `resolvePieceSample`, `compilePieceCameraTrack`, `getPieceTransportDurationMs`.

Last visible State cannot be hidden. Same stickiness as last cannot be deleted.

Focused gap whose either endpoint is hidden does not set a loop window and does not scrub. The inspector still binds so authored duration can be edited for when the eye comes back.

`EyeIcon` moves out of `StructureSliceLayer.tsx` into `src/panels/EyeIcon.tsx`. Shared `.cc-eye` chrome.

## Synthesis decision

Base is authored hide (candidate A). Session shy (candidate B) lost because the strip and the take would disagree. Filtering cards remaps transitions by index and invents a neighbor pair. Play would still visit the hidden pose.

No graft from B.

## Tradeoffs accepted

- We accept persist and codec edits in exchange for hide surviving reload and undo.
- We accept a shorter playable clock in exchange for not showing a hidden pose and not inventing an 11 to 13 morph.
- We accept dimmed Transition cards that still show authored milliseconds even while those gaps do not play.
- We accept that assembly still hands off at authored `startMs` onto the first presentable State.

## Alternatives considered

- Session `hiddenStateIds` plus shy collapse. Smaller persist surface. Strip and play disagree. Rejected.
- Hide the State card and both Transition cards. 11 sits against 13. Looks like a new authored gap. Rejected.
- One synthetic 11 to 13 card using the outbound settings. Invents motion authored for a different pair. Rejected.
- Reuse `set-cube-visibility-intent`. Wrong document layer. Rejected.
- Keep authored time and cut the pose in place. Loop windows stay valid, but the take still spends time on a hidden State. Rejected for v1.

## Open questions and risks

- Should a hidden first State retarget Build-in assembly into the first visible pose? v1 holds the first presentable State through `startMs`.
- Delivery budget will move. Re-baseline after the feature lands, same as the last motion PRs.

## Next implementation step

Add `hidden?: true`, `set-state-hidden`, and `presentableStateTransitionTrack`, then wire persist, strip eye, and the three playable callers.
