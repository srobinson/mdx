# Slice 2 adversary: Transition inspector panel (arrangement control, counts, empty tabs)

**Seat:** ADVERSARY  
**Branch:** `feat/transitions-ux` @ `4832ead`  
**Stance:** try to break what the other seats are about to build, before it is built.  
**Constraint:** read-only; no patches; no subagents. Temporary vitest probes run under `/tmp` naming and deleted; worktree clean after.  
**Evidence tags:** **probed** (vitest against this SHA), **structural** (code/type read), **prior** (earlier briefs, not re-probed).

---

## What is already true at this SHA

Slice 1 is merged on this branch (`a7e0b88`, `ea65997`, `1ce73da`). Arrangement is first-class and continuous:

| Fact | Owner | Evidence |
|---|---|---|
| Per-endpoint offsets | `prepareSceneMorphTopology` → `arrangement.from/to` via `getSceneGridAlignment` | **structural** `evaluation/sceneMorph.ts` |
| Continuous crossing | `sampleSceneMorph` lerps `arrangementOffset` with `arrangementProgress` | **structural** + **probed** |
| Progress clock | `resolveEditorArrangementProgress(durationMs, timeMs)` = linear `time/duration` | **probed** 0.25 and 0.75 |
| Endpoints are canonical | `endpointFrame` omits `arrangementOffset`; layout falls back to endpoint alignment | **probed** start/end `arrangementOffset === undefined`; mid at t=0.5 is `[-0.375,0,0]` for 1→2 |
| No policy field | `MorphSettings` has `arrive/depart/glide/cutAt/durationMs` only | **structural** `domain/morphSettings.ts` |
| No arrangement UI | `MorphInspector` has Duration, Scene switch, Cubes tabs, Order, Stagger, Easing, Steps | **structural** |
| MOVING no longer drives arrangement | Pre-slice-1 model docs said grid/arrangement used `plan.changed.motion`; at this SHA arrangement uses the linear progress arg, not glide easing | **structural** (model doc `cubicell-ux-transition-model.md` is partially obsolete) |

### Probe matrix (1→2 one-sided +x growth, default grid step 1.5)

| Policy (simulated) | `cube-0-0-0` home X | Price |
|---|---|---|
| Continuous (shipped) | start `0` → mid `-0.375` → end `-0.75`; first interior ~continuous | **probed** |
| Snap (`progress=1` at t≈0) | start jolt `-0.75` | **probed** = the fixed defect |
| Hold mid-gap (`progress=0`), terminal endpoint canonical | end jolt `-0.75` per asymmetric growth | **probed** |
| Hold freezes endpoints to S1 alignment | S2 drift `+0.75`, S3 `+1.5`, S4 `+2.25` on retained cube | **probed** progressive composition walk |

Ink-only change (via `createInkTweenEndpoint`): `changedIds` size 1, `colorInkIds` size 1, arrangement delta `[0,0,0]` → pure recolour is MOVING, not ENTERING. **probed**

---

## 1. The control's right to exist

### Strongest case: ship panel work, ship **no** arrangement control

1. **The bug is fixed and made unconditional on purpose.** Continuous crossing is the correct layout behaviour. A control that reintroduces Snap (or Hold that defers Snap to the endpoint) is productising the defect under friendlier names. **probed** Snap jolt = `-0.75`, identical magnitude to the pre-slice-1 start jolt.
2. **There is no MorphSettings channel to flip.** Adding `Snap | Ease | Hold` is a new persisted field on `Transition.settings` → schema version bump and full reset under the project's no-migrations policy (**structural** persistence codecs version fields). That is a high tax for a policy whose best option is "do what we already do."
3. **Cut already covers hard composition change.** `TransitionMode "cut"` swaps whole scenes at `cutAt * durationMs` with `moment: null` (**structural** `sampleSceneTransition` + `score.ts` NOTE). Instant composition change is a cut, not an arrangement Snap. Shipping Snap next to an unsurfaced Cut confuses two different hard-switches.
4. **Hold is not a style; it is a debt.** Two priced Hold semantics both lose:
   - Gap-only hold, endpoint canonical: deferred jolt of **0.75 world units per asymmetric growth** at every gap end (**probed**). Authors feel "smooth" mid-gap and get slapped at the settle.
   - Endpoint freeze / retained-anchor: progressive drift **0.75 · n** after n one-sided growths, and absolute camera desync of the same magnitude because `StateCameraView` stores absolute world poses authored against canonical centres (**probed** freeze chain; **structural** `bindViewToState` / `CameraPoseSnapshot`).
5. **Ease as the only continuous option is not a three-way control.** Linear progress is already Ease with identity easing. A curve knob (if anyone needs it later) is not Snap|Ease|Hold.
6. **LESSONS.md does not force this control.** `LESSONS.md` (2026-08-03) says the unit of merge is the feature, and slice 1 alone was incomplete because it shipped a behaviour change with no controls. That is a process rule against merging partial features to main. It is not a product rule that every fixed layout defect must grow a segmented peer of CUBES. Completing the feature can mean inspector honesty (what each class owns) without resurrecting opt-outs.

### Strongest case against that case (steelman for the control)

1. **Authors may want survivors visually still while new mass appears off-centre** (Hold intent). Continuous recentre always translates retained cubes whenever extent centres differ. That translation is real motion on screen with no morph class owning it in pure growth (`changedIds` empty, **probed**). A Hold that freezes mid-gap answers the "I did not ask that cube to move" complaint differently than continuous does.
2. **Film language sometimes wants a hard reframe** (Snap intent): smash-cut composition at the start of a growth beat.
3. **Without any arrangement surface, the inspector still lies by omission:** pure growth still shows MOVING empty while the retained cube translates under continuous crossing. The control, paired with a frame readout, is the only proposed owner for that motion.
4. **Process pressure:** feature branch merge wants a finished story; continuous-only with no mention in the panel leaves the seam invisible.

### Does the control survive?

**No as Snap|Ease|Hold.** That trio fails the steelman: Snap is cut's cousin and the measured defect; Hold's two implementations are end-jolt or progressive desync; Ease is status quo.

**Only if reduced to a job nothing else does:**

| Candidate job | Survives? | Why |
|---|---|---|
| Opt out of continuous crossing (Snap) | **No** | Reintroduces the defect; cut mode is the hard switch |
| Freeze retained world positions across gaps (Hold) | **No** without an authored composition origin and camera rebake story; priced drift **0.75·n** and camera desync |
| Curve of continuous crossing (linear vs eased) | **Maybe later** | Distinct from Snap/Hold; not required for slice 2 honesty; today linear is fine |
| Readout that arrangement is crossing and by how much | **Yes, as copy** | Not a control; owns the "classless translation" explanation |

**Withdraw condition for "no control":** a written Hold semantics that (a) never changes steady-state endpoint layout, (b) never end-jolts, (c) rebakes or relative-ises `StateCameraView`, and (d) is not reachable as a one-click opt-out of continuity. None of the straw options satisfy (a–d).

---

## 2. Opt-out options priced

### Hold

| Cost | Magnitude | Evidence |
|---|---|---|
| Deferred settle jolt if endpoints stay canonical | **0.75 u** per 1→2-class growth (half grid step) | **probed** `endJolt` / `endJolt23` |
| Progressive rest drift if endpoints freeze to early alignment | **0.75 · (stateIndex−1)** on retained cube for successive +x growth | **probed** freeze chain to S4 = **2.25 u** |
| Camera view desync | Same deltas as freeze chain; views are absolute world poses | **structural** `domain/cameraTrack.ts:StateCameraView`; **probed** layout deltas |
| Path dependence | Composition after a Hold chain is a function of first state's centre, not author intent | **probed** freeze chain |
| Next gap inherits wrong baseline only under freeze semantics | If rest is non-canonical, next `arrangement.from` changes meaning | **structural** topology always resolves from endpoint cells; freeze would have to corrupt endpoints or insert a phantom offset store |

Costs nobody named earlier (additions):

- **Double clock with ENTERING:** Hold freezes arrangement while arrive stagger plays; newcomers appear relative to a frozen origin then (on end-snap) the whole lattice jumps. Two motions fight. **structural** schedules independent; **unverified** feel (no live UI).
- **Thumbnail / Frame All honesty:** endpoints omit offset today; Hold-freeze would make live rest disagree with thumbnails that layout endpoint poses canonically (`thumbnail` path uses `createSceneGridLayout(pose.grid, pose.cells)`). **structural** prior scout; thumbnail path not re-probed this seat.
- **Comparison scrub** hardcodes `defaultMorphSettings` (**structural** `stagedScene.ts`); any new Hold field must flow there or scrub and playback disagree.

### Snap (now that continuous is default)

| Cost | Magnitude | Evidence |
|---|---|---|
| Reintroduces measured start jolt | **0.75 u** at first interior frame | **probed** |
| Teaches authors the bug is a style | n/a product cost | prior adversary + this probe |
| Collides with Cut vocabulary | Instant whole-scene swap already exists as `mode: "cut"` | **structural** |
| Breaks the "jolt is gone" story of slice 1 | Feature narrative regresses | process |

### Ease (status quo continuous)

Cost of *not* shipping it as a named option: none behavioural; only discoverability of the seam. That is a readout problem, not a three-way segmented.

---

## 3. Counts in tab labels ("Entering 2")

### Attack

1. **Wrong idiom.** Counts in this UI are prose readouts: `SelectorPanel` `Set {n}`, `StructureSection` cell count, `SelectionSection` delete labels, `SpatialResult` match summary (`cc-panel-readout` / `cc-spatial-match-count`). Segmented options take plain labels only (`components/ui/segmented/Segmented.tsx`: `{ label, value }`). **structural**. Label counts invent a third pattern.
2. **Prior rejection of badges still applies to labels.** Same information density, same "number on the bucket" shape; moving the number into the string does not change the trap from `cubicell-ux-adversary.md`: counts certify emptiness under a taxonomy that still leaves pure-growth translation classless (`changedIds` empty while arrangement moves, **probed**). `Entering 1` + `Moving 0` while the retained cube eases −0.75 is a quieter lie than before, not the truth.
3. **When no transition is selected:** `TransitionInspector` renders "Select a transition card…" with no topology (**structural**). Counts have no subject; any host that still paints CUBES must invent zeros or hide the strip. Spec that.
4. **Mid-edit:** topology is endpoint pair of the gap's States, not the live working scene (**structural** `prepareSceneMorphTopology(a,b)`). Counts can disagree with what the user is looking at while sculpting before Update.
5. **Empty class:** `Entering 0` restates what dimming already says; noise on every pure-pose or pure-leave gap.
6. **Large counts:** segmented buttons are equal flex siblings; `Entering 128` / `Leaving 64` wraps or crushes Order/Easing peers. **structural** (no truncation in Segmented); **unverified** exact pixel wrap.
7. **Prose beats label counts.** Existing convention is sentence or `cc-panel-readout` beside a section title. A muted line `2 cubes entering` (or active-class sentence in the `morphClassHints` slot) matches the product and leaves the segmented control scannable. Prior panel seat already preferred prose over label counts (`cubicell-ux-transition-panel.md` §6.2); that remains the better of the two count surfaces.

### Withdraw condition

Counts in labels only if (a) pure-growth classless translation is owned somewhere so `Moving 0` cannot appear while a cube translates, (b) Segmented gains a designed dense label treatment used product-wide, and (c) zero is never shown (dim only). Until then: prose readout, not `"Entering 2"`.

---

## 4. Empty tabs: dimmed but editable, and auto-select

### Dimmed but editable is a trap

| Claim | Evidence |
|---|---|
| Not-applicable elsewhere means **disabled**, not soft-dim editable | `SelectionSubjectControl`: unavailable subjects `disabled: true`. `PanelTabs` / `SelectorPanel` disable unavailable tabs. **structural** |
| Dimmed-in-place for N/A is real, but coupled with non-activation | Spatial options that are disabled stay visible and muted; they do not accept edits. **structural** |
| Empty morph class values still persist and apply later | `patchMorphSettings` always stores arrive/depart/glide; empty class still has settings. **structural** |
| Contradiction | Dimming says "not applicable now"; editability says "applicable to author." Users either ignore the dim and thrash dead knobs, or trust the dim and never pre-author the empty class. Both fail a different goal. |

What breaks:

1. **Discoverability inversion:** dimmed LEAVING/MOVING in a pure ENTERING gap trains the user to ignore those tabs; when they later need MOVING, the habit remains. **prior** adversary + **structural** auto-focus on non-empty.
2. **False confidence:** editing dimmed STEPS/EASING "for later" with no live preview (class empty) produces settings the user cannot validate until topology changes; then a surprise motion appears. **structural**
3. **A11y:** dim without `disabled`/`aria-disabled` is a visual-only signal; screen readers still announce full controls. **structural** Segmented has no dimmed API today.

**Withdraw condition:** either dim+disabled (cannot edit empty class), or full-strength always (can pre-author), with prose saying the class is empty. Not both dim and edit.

### Auto-select first non-empty class

Today: `useState<MorphClassId>("arrive")` in `TransitionInspector` (**structural**). Local React state; reopening defaults to Entering regardless of topology.

Attacks on auto-select of first non-empty (ENTERING → LEAVING → MOVING):

1. **Steals deliberate empty selection.** User opens LEAVING to pre-author a future leave, toggles away and back (or remounts inspector on focus change): selection jumps to ENTERING if leave is still empty. Authoring into empty is exactly the case dim+editable claims to support; auto-select fights it.
2. **Topology churn.** Live state edits that empty/fill classes while the inspector is open would re-pick under a naive effect; selection becomes a function of the lattice, not the user's last click. **unverified** whether focus remounts; risk is real if implemented as `useEffect` on topology.
3. **Identical-state gap.** All empty → stay on ENTERING dimmed; auto-select does nothing useful and still shows class controls for a no-op transition.
4. **Wrong priority for pure recolour.** First non-empty is MOVING only when added/removed are empty; good for recolour (**probed** ink → changed). First non-empty for pure growth is ENTERING, which is correct for the enterers and still leaves arrangement motion unowned.

**Withdraw condition:** auto-select only on first open of a given `keyframeId`/transition index, never on topology change, and never override an explicit user tab click in that session. Prefer sticky last class per transition index.

---

## 5. The thing nobody has asked: Cut mode and MOVING rename

| Item | Domain status | Editor status |
|---|---|---|
| `TransitionMode "cut"` | Working: whole-scene swap at `cutAt * durationMs` | No control; `patchTransition` UI only patches `MorphSettings`, never `mode` (**structural** `MotionInspector` / `score.ts` NOTE) |
| MOVING label | `glide` / `changedCells` includes pose **and** ink (recolour/opacity) | Label says "Moving"; hint says "Cubes shared by both states" which is closer but still implies motion (**structural** + **probed** ink ∈ changed) |

### Separable from slice 2 panel chrome?

**Yes for shipping mechanics.** Arrangement continuous crossing, tab counts, dimming, and auto-select do not require Cut UI or a MOVING rename. Domain already separates `mode` from `settings`.

### Incoherent if slice 2 ignores both?

**Partially.**

- **Cut:** The inspector already exposes **Scene switch** (`cutAt`) with no statement of what switches and no Cut vs Morph mode. Slice 2 adding more gap-wide chrome without surfacing Cut leaves the only real hard-switch half-documented. Not a blocker for counts/dim, but a coherence debt if any arrangement Snap is proposed (Snap ≈ hard arrangement switch; Cut ≈ hard scene switch). Prefer surfacing Cut over inventing Snap.
- **MOVING rename:** Pure recolour is already a first-class changed cell (**probed**). Leaving the label "Moving" means counts like `Moving 1` on a colour-only gap teach the wrong verb. Rename is separable and cheap (copy only) relative to Cut UI; shipping counts that say `Moving N` for recolour **amplifies** the misnomer. If slice 2 adds counts, rename is no longer optional for honesty.

**Verdict:** separable as engineering tasks; **not** separable as panel truth if counts ship. Cut can wait; MOVING naming should land with any count surface.

---

## Objection register (priced, withdrawable)

| # | Objection | Price | Withdraw when |
|---|---|---|---|
| O1 | Arrangement Snap\|Ease\|Hold control has no right to exist | Snap = **0.75 u** start jolt; Hold end-jolt **0.75 u**/growth or freeze drift **0.75·n**; schema bump; confuses Cut | Control reduced to continuous-only curve or removed; Snap/Hold deleted |
| O2 | Hold progressive drift + camera desync | **0.75 → 2.25 u** over 3 growths; absolute views aim wrong | Authored composition origin + camera rebake/relative views specified and implemented |
| O3 | Snap is the old defect with a name | Full regression of slice 1 story | Snap never ships |
| O4 | Label counts break product count idiom and decorate classless translation | Taxonomy still shows `Moving 0` during continuous arrangement move on pure growth | Class or readout owns arrangement motion; counts use prose idiom |
| O5 | Dimmed-but-editable contradicts N/A = disabled | Prestaged settings without preview; a11y hole | Pick dim+disabled **or** full-strength editable |
| O6 | Auto-select steals empty-tab authoring | Breaks the only coherent use of pre-authoring empty classes | Once-per-open sticky selection, never topology-driven |
| O7 | Cut unsurfaced + MOVING misnames recolour | Counts amplify "Moving" on ink-only gaps; Snap would twin Cut | Rename MOVING with counts; prefer Cut UI over Snap |

---

## Single strongest objection

**Do not ship an arrangement policy control (Snap|Ease|Hold).** Slice 1 already made continuous crossing the unconditional correct behaviour; Snap is the measured defect (−0.75 u), Hold is either a deferred jolt of the same size or progressive camera-desynced drift (0.75·n), and Cut already covers intentional hard switches. Ship inspector honesty (prose class readouts, fix empty-tab semantics, rename MOVING if counts exist) without reopening the jolt as a preference.

---

## Probes run

Temporary vitest files under `tests/__adversary_probe*.test.ts`, executed with `pnpm exec vitest run … --project unit`, then deleted. Worktree clean. SHA `4832ead`.

Symbols cited: `prepareSceneMorphTopology`, `sampleSceneMorph`, `resolveEditorArrangementProgress`, `endpointFrame`, `MorphSettings`, `MorphInspector`, `TransitionInspector`, `resolveTransitionKind`, `sampleSceneTransition`, `StateCameraView`, `Segmented`, `createInkTweenEndpoint`.
