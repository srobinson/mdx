# Cubicell campaign runway: implementation spec

Date: 2026-08-07. Authority: scout report `cubicell-scout-face-choreography.md` (reuse map), consensus condition set A, B, C', D', E, F, G from the four wedge verdicts. Repo: main `7d5e942`; stencil branch `feat/stencil-build` at `66b4d8d`.

## Bound decisions (closed, do not reopen)

1. Cut mode exposure builds first (condition E).
2. `CubeFaceFigure.fit` is kept; shader honour lands only on the first optical break (registry, slice 5).
3. Concierge seeding, one commit per mark (condition C'); runtime ingestion stays frozen.
4. Capture stays wall-clock webm; the fixed-step clock lands only on a visible seam break (registry).
5. Figure authoring stays stencil enum plus `defaultFigure`; region/colour bindings land only on a repeated break (registry).
6. Doc reconciliation happens during the runway, not after.

Dependency, not a slice here: the Library-bypass repair (condition F) is building on `fix/stencil-library` (based on `66b4d8d`). Slices 3 and 4 sign-off assume it merged; nothing below respecifies it.

Gates, all slices: inner loop `pnpm check` and `pnpm test`; merge authority `pnpm test:all` and `pnpm check:budget`. Every new test must first fail against the pre-slice tree (controlled red) before the change lands.

## Slice 1: MorphInspector authors Transition.mode

**Goal.** Surface the built, tested whole-scene cut so a beat cut is authorable from the Editor (condition E). No new capability: the pipeline already carries `mode` end to end.

**Reuse-map bindings.**
- `src/domain/score.ts` — `TransitionMode = "auto" | "cut"`, `Transition`; the file's own NOTE marks cut as working, tested, unexposed.
- `src/domain/stateTransition.ts` — `TransitionPatch.mode`, `patchTransition` (already honours `patch.mode`), `defaultTransition`.
- `src/domain/structureSequenceOperations.ts` — the `patch-transition` operation already declares `mode?: TransitionMode`; `src/domain/authoredInverse.ts` already inverts it.
- `src/evaluation/sceneTransition.ts` — `resolveTransitionKind`, `sampleSceneTransition` forced-cut path at `cutAt * durationMs`.
- UI gap, the only build: `src/panels/motion/MorphInspector.tsx` (`MorphInspectorProps.onTransitionChange` currently emits only `Partial<MorphSettings>`) and `src/panels/motion/MotionInspector.tsx` (its `patchTransition` closure dispatches `patch-transition` without `mode`).

**Deliverables.**
- A two-value mode control in `MorphInspector` (auto | cut), styled beside the existing `cutAt` control it governs.
- `MotionInspector` threads `mode` into the existing `patch-transition` dispatch. No new operation kind, no new state owner.
- Cut hides or disables the per-class motion controls that a forced cut ignores, matching what `sampleSceneTransition` actually evaluates.

**Tests.**
- `tests/morphInspector.test.tsx`: authoring the mode control dispatches `patch-transition` with `mode`. Red first: the assertion fails today because no control exists.
- `tests/activeTransitionPlan.test.ts` or a focused `sceneTransition` unit: an authored `mode: "cut"` transition swaps the whole scene at exactly `cutAt * durationMs`, both sides of the boundary sampled. Red first by asserting through the UI-authored patch path.
- Undo round-trip: `patch-transition` with `mode` inverts through `authoredInverse`.

**Done.** A user can author a beat cut from the inspector, it survives undo and persistence, and the boundary sample lands where `cutAt` says.

## Slice 2: doc reconciliation

**Goal.** Future specs inherit true status; the runway must not be planned against stale claims (scout Quality Map items 2 and 3).

**Reuse-map bindings.** Three ANIMATION.md passages claim the camera track is undriven: invariant 2 ("no production caller"), the Track primitive passage ("no evaluator or production surface"), and the Score/Track section ("no evaluator samples it yet"). All three are contradicted by the live production possession loop: `src/studios/editor/useCameraTrackFrame.ts`, fed by `src/domain/pieceCameraTrack.ts` — `compilePieceCameraTrack` and `src/evaluation/cameraTrackSampleAt.ts` — `cameraTrackSampleAt`. `ANIMATION.KNOBS.md` rates quantize, order modes, cadence curves, and disassembly `[near]`; all are shipped (`ClassMotion.quantize`, `OrderMode` in `src/domain/assemblyOrder.ts`, `CadenceCurve` in `src/domain/assemblyTiming.ts`, `AssemblyExit` in `applyAssemblyTrack`).

**Deliverables.** Correct the three ANIMATION.md camera passages to name the shipped possession loop; retag the four drifted knob entries `[now]` with their owning symbols; add slice 1's mode control to the knob catalogue when it lands. No other editorial changes.

**Tests.** None executable; the gate is review. Verification: `grep -n "drives it yet\|samples it yet" ANIMATION.md` matches all three passages today (the file is hard-wrapped, so patterns spanning "no" plus the claim miss two of them) and returns nothing after reconciliation, and no `[near]` tag remains on a shipped symbol.

**Gates.** `pnpm check` (docs touch nothing typed, but the gate stays the merge floor).

**Done.** ANIMATION.md and ANIMATION.KNOBS.md agree with the code they describe at the runway's head.

## Slice 3: concierge seeding recipe

**Goal.** A documented, repeatable per-mark procedure (condition C': one commit per mark) so campaign marks enter through the existing resolver and atlas with gates, not ad-hoc builds.

**Reuse-map bindings.** `src/domain/seededStencils.ts` — `seededStencils`, `resolveStencilContent`; `src/domain/stencil.ts` — `createStencilId` (`sha256:` content-addressed); `src/scene/stencilAtlas.ts` — `stencilAtlasCapacity` (16 slots, 2 occupied, 14 free), `slotByStencilId` built at module load; `src/editor/controlBindings.ts` — `faceStencilBinding` options enumerate the registry. All at `66b4d8d`; the recipe activates once `feat/stencil-build` plus `fix/stencil-library` merge.

**Deliverables.** A recipe section appended to `TYPOGRAPHY.md` (existing doc home for mark guidance) specifying per mark: (1) prepared outlined SVG in `assets/marks/<name>.svg`, two-value composition per the synthesis contract; (2) one `seededStencils` entry with name, region, fit, colour defaults and a `createStencilId` hash; (3) budget rebaseline; (4) one commit per mark, message `feat(assets): seed <name> mark`. Plus a running slot ledger in the same section recording, per mark: slot consumed (14 free at start; overflow stops the content plan rather than expanding the atlas), seeding wall time, and rebuild count — the last two are the provisioned source for slice 5's scoped-ingestion trigger.

**Tests.** Per mark, no new test files: `tests/faceStencilRender.test.ts`, `tests/stencilRendering.browser.test.ts`, and `tests/stencilAssets.test.ts` must pass with the new entry, and the resource assertions (one atlas texture, no churn) are the controlled invariant. Each new mark first updates the two roster expectations in `tests/stencilAssets.test.ts` (the exhaustive `seededStencilAssets` roster and the full-list expectation) before running the controlled red, so the red isolates the hash. Controlled red for the recipe itself: a deliberately wrong declared hash cannot fail resolution (`resolveStencilContent` resolves through `seededStencilsById`, keyed on the declared `asset.id`, so a bad hash still resolves); the red binds instead to the hash-integrity assertion in `tests/stencilAssets.test.ts` — `createStencilId(content.source) === asset.id` — which is the only place a wrong hash fails at `66b4d8d`. The recipe's red step: with rosters already updated, land the entry with a placeholder hash, watch that assertion alone fail, then correct it.

**Gates.** Per mark commit: `pnpm check`, `pnpm test`; before any campaign use: `pnpm test:all`, `pnpm check:budget`.

**Done.** Any agent can land a campaign mark in one gated commit by following the recipe, and the slot ledger shows remaining capacity.

## Slice 4: campaign pass/fail sheet

**Goal.** Condition A made concrete: the pre-committed external, numeric criteria exist as a committable artifact the owner signs before piece one, so the campaign can visibly fail.

**Reuse-map bindings.** Criteria source: the fable verdict's five-question section (`cubicell-wedge-verdict-fable.md`). Q4's overlap measurement binds to persisted structured state: `src/domain/score.ts` — `Score`, `ScoreTrack`; `src/persistence/indexedDbProjectStorage.ts`.

**Deliverables.** New root doc `CAMPAIGN.CRITERIA.md` (matching root doc convention) containing, verbatim as pre-commitments:
- **Q1 distinctness:** blind panel of ≥10 uninvolved viewers; ≥70% correct track-to-visual matching against a 33% baseline; ≤3 of 10 answer "same piece re-skinned".
- **Q2 depth:** same-day session logs written before review; pass if piece-3 logs record ≥1 adopted unplanned discovery and engagement has not declined monotonically 1→3. The log template carries the fields the trigger registry (slice 5) measures from, per session: engagement score 1–5, unplanned discoveries, retime wall-time after any arrangement edit, a per-piece count of default-override workarounds (figure authoring reached only through `defaultFigure`), and any optical failure naming the mark and face with a committed screenshot.
- **Q3 speed:** wall-clock hours per piece including concierge steps (SVG prep, audio mux, transcode); piece 1 ≤40 h (owner may re-anchor before piece one, then the number is fixed); piece 3 ≤60% of piece 1 at equal or better Q1 distinctness. The sheet also pre-commits the retime threshold: maximum acceptable retime wall-time per arrangement edit, fixed before piece one, consumed by the tempo-field trigger in slice 5.
- **Q4 authorship:** no piece pair shares >30% authored scene, choreography, and palette state (engine defaults excluded), measured by a state diff over persisted `Score` data; the "authored" definition is fixed in the sheet before piece one.
- **Q5 return:** pass only on external behaviour (an outside musician or VJ uses a piece for a real release or set and requests a second); otherwise recorded as explicitly deferred, never self-scored.
- Condition B stated on the sheet: a full pass claims engine validation only, no product-home claim.
- A signature line: owner name and date, required before piece one begins.

**Tests.** None executable at spec time; the Q4 diff script is specified here but built only when piece two exists (first moment two pieces can be diffed). Its controlled red: two identical projects must measure 100% overlap, two disjoint projects near 0%, before the 30% line is trusted.

**Gates.** Commit gate only (`pnpm check` floor); the sheet's own gate is the owner signature.

**Done.** `CAMPAIGN.CRITERIA.md` is committed and signed before piece one, and every question on it can fail.

## Slice 5: evidence-trigger registry

**Goal.** Every deferred unfreeze consolidated in one committable place, each with its trigger condition and measurement, so capability lands on evidence rather than appetite and no deferral is silently forgotten.

**Reuse-map bindings and entries.** New root doc `CAMPAIGN.TRIGGERS.md`, one row per deferral:

| Deferral | Bound symbols | Trigger | Measurement |
| --- | --- | --- | --- |
| `fit` honour | `faceStencilShader.ts` — `fitFlag` packed, fragment never reads it; `CubeFaceFigure.fit` | First optical break: a campaign mark unusable at margin/bleed defaults | The Q2 log's optical-failure fields (mark, face, committed screenshot), provisioned in slice 4 |
| Fixed-step export clock | `src/state/actions/transportActions.ts`; `src/export/streamRecorder.ts` — `createRecordingController` | Visible seam break in a recorded loop | Boundary-frame comparison of the recorded webm (first/last frame image and camera pose) fails declared tolerance |
| Figure bindings (region, colour, fit controls) | `src/editor/controlBindings.ts` — `face.stencil` only today | Same authoring break logged in two different pieces | The Q2 log's per-piece default-override workaround counter, provisioned in slice 4 |
| Tempo field (project BPM, bar-snapped durations) | `MorphInspector` duration field; `getStateTransitionDurationMs` | The retime threshold pre-committed in `CAMPAIGN.CRITERIA.md` (Q3 section, slice 4) exceeded | The Q2 log's retime wall-time field, compared against that threshold |
| Scoped runtime ingestion | `StencilAsset`, `createStencilId`, `seededStencils` seeding path | Seeding recipe hurts on three marks, or Q5 passes green post-campaign | Per-mark seeding wall time and rebuild count from the slot ledger (slice 3) |

Each row also names its landing shape (one slice, owner and test file) so the unfreeze, when triggered, starts from a spec line rather than a debate.

**Tests.** None executable; the registry's gate is that every trigger references a measurement already being collected by slices 3 and 4 (session logs, slot ledger, criteria sheet). A trigger with no live measurement source is a spec defect.

**Gates.** Commit gate (`pnpm check` floor); review confirms the measurement-source rule.

**Done.** `CAMPAIGN.TRIGGERS.md` is committed with all five deferrals bound to symbols, triggers, and live measurements, and no deferred capability exists outside it.

## Order

Slice 1 → slice 2 (same PR window, condition E first) → slices 4 and 5 (paper, parallel) → slice 3 activates on the `fix/stencil-library` merge → piece one begins only after the criteria sheet is signed and the repair is merged.
