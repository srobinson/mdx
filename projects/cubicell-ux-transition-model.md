# Cubicell — the conceptual model of a gap

Seat B. Ideation only, read-only, no panel layout. The job is to attack the model.

Verdict up front: the orchestrator's framing is wrong in three places. FRAME is not a
peer of CUBES because "frame" names three different actors and the one that actually
moves is the camera. The two-tier split (gap-wide / per-population) is the wrong seam;
the real seam already present in the code is **tween vs. switch**. And dimming empty
populations treats a lie as a display problem: the panel's worst statement is not
"Entering 0", it is "Moving 0" while the picture moves, and no amount of dimming
touches it.

---

## 1. What actually moves across a gap

The domain already answers this and the panel ignores the answer. `Pose` in
`domain/scene.ts` is `CubicellScene` minus `score`: exactly the set of things a gap
carries from one State to the next.

| Actor | Field | How it crosses |
|---|---|---|
| The cubes | `cells` | tween, per class (`arrive` / `depart` / `glide`) |
| The lattice | `grid` | tween (`interpolateGridState`: `cellSize`, `gap`, `gapOverrides`, `origin`) |
| The coordinate frame | `frameId` | **switch** at `cutAt` |
| Polarity | `polarity` | **switch** at `cutAt` |
| Projection | `projection` | **switch** at `cutAt` |
| Alignment / overflow | `grid.format.align`, `.overflow` | **switch** at `cutAt` |
| The camera | `StateCameraView` (outside the scene) | tween, `CameraPosePath` = cut / linear / orbit |
| The arrangement | none — derived | **steps**, twice, uncontrolled |

Two entries on that list are not in the panel at all, and one is not in the codebase
as a thing.

**The camera.** `cameraTrack.ts` states the KISS model outright: "playback is simply
the transition between consecutive States' captured views." A camera move is the most
visible thing that can happen across a gap, it has its own path vocabulary
(`CameraPosePath`), and the Transition inspector offers nothing for it. The transport
carries `CAPTURE VIEW → STATE 1`; the gap that plays the move carries no control.

**The arrangement.** `getSceneGridAlignment` recentres over whatever cell set it is
handed. `sampleSceneMorph` hands it different sets at different times: at `timeMs <= 0`
`endpointFrame` returns `plan.a`, mid-gap the scene is B's cells plus `removedCells`,
at `timeMs >= durationMs` it returns `plan.b`. So the alignment input steps A → A∪B → B.
Alignment is a pure step function of that set, so the picture takes a discontinuity at
each gap boundary. The measured 0.75 for a one-sided 1→2 is exactly half a grid step
(`getGridStep`), i.e. the change in the extent's centre; symmetric 1→3 measures zero
because the centre does not change. That reconciles the measurement with the code, and
it is the whole of complaint 1. *(Inference from reading `sampleSceneMorph` and
`getSceneGridAlignment`; the 0.75 and the zero are the orchestrator's measurements, the
A∪B account of them is mine and unprobed.)*

The consequence matters for the panel: **the jolt is not a control problem.** No
naming, no tab, no dimming fixes a step function. Any model that only reorganises the
panel ships complaint 1 untouched.

**The finding that resolves complaint 2.** In `sampleSceneMorph`, the lattice tween is
driven by `plan.changed.motion` — the MOVING tab's easing and its `quantize` — sampled
at `globalProgress`. The MOVING tab therefore governs a second, unnamed thing, at a
different clock from the cubes it names, in every gap including gaps where MOVING
counts zero. The user's "I make the same change on all three tabs just to be safe" is
not superstition. It is the correct empirical response to a panel in which one of the
three tabs has a hidden extra job.

---

## 2. Is FRAME a peer of CUBES?

No, and the question hides an ambiguity. "Frame" in this product names three unrelated
actors:

1. `frameId: CoordinateFrameId` — the coordinate frame the State is authored in. It
   **switches**. It does not move. Promoting it to a peer of CUBES and giving it motion
   controls would be a behavioural change smuggled in as a panel change.
2. The captured camera view — this genuinely moves, and is genuinely a peer.
3. The visible framing (where the picture sits, how big it reads) — derived from the
   arrangement, authored by nobody.

Calling all three "the frame" is how a panel ends up with a control that does nothing.

**The strongest alternative decomposition: tween vs. switch.** It is not invented; it
is already the code's spine. One number, `cutAt`, threads through `sampleSceneMorph`
as `globalCut` and through `interpolateCell` as `afterCut`, and it governs every
discrete channel at once: `frameId`, `polarity`, `projection`, `align`, `overflow`,
per-cell `visibility`, face `visible`, and grid `coord`. Everything else lerps.

What it buys:

- **`SCENE SWITCH 0.50` stops being a mystery number.** Today it is a bare field next
  to DURATION with no statement of what it switches. Under this decomposition it owns
  a named list, and in a gap where nothing discrete differs it has nothing to own and
  can say so.
- **It explains the jolt in the user's own terms.** Something switched that they
  thought would move. That is the sentence they need.
- **It is closed.** "Gap-wide vs. per-population" leaves the arrangement and the
  camera homeless. Tween-vs-switch places every field of `Pose` plus the camera, with
  no residue.

Subject-vs-observer is the runner-up and it is worth keeping as a second axis: cubes
and lattice are the subject, the camera is the observer, and conflating them is why a
camera move currently reads as the cubes moving. But it does not classify `polarity`
or `frameId`, so it cannot be the primary cut.

---

## 3. Should the three tabs exist?

**For.** They are discoverable: three visible tabs advertise that entering, leaving,
and moving *can* differ. They keep the panel short. They match the data model
(`morphClassIds` = arrive / depart / glide) exactly, so there is no translation layer
to get wrong. Progressive disclosure that hides the split risks a user who never
learns the capability exists, which is worse than a user who over-edits.

**Against.** A tab bar is hidden state, and the panel gives no signal about the
inactive tabs: the user cannot see that LEAVING's stagger is 40 without leaving the
tab they are on. Editing all three is the rational response. Worse, the tabs promise a
symmetry the engine does not honour — MOVING secretly also drives the lattice, so the
three are not peers.

**Commit: remove the tabs. One motion for the gap, split on demand.**

A gap has one motion by default: one ORDER, one STAGGER, one EASING, one STEPS,
applied to whatever the gap contains. A population is split out only when the user
asks for it, and only populations that exist can be split. This answers complaint 2
directly (one edit covers everything, which is what the user was already trying to
express by editing three times) and complaint 3 (a control for a population that does
not exist is never rendered).

One correction to the brief's evidence. `STUDIO.ANIMATION.md` lists "Arrival, Stagger,
Order, Easing, Start delay, Loop" for a **selected Piece**, whose build-in has exactly
one population by construction — everything arrives. It is therefore weak evidence for
collapsing gap classes; it is not a considered position on gaps at all. The doctrine
that *does* apply is the same document's "Keep controls contextual… Sophistication
comes from depth, not simultaneous density." Cite that, not the Arrival list.

---

## 4. Naming: failure of words or of affordance?

Both, and they compound. But there is a sharper diagnosis than either: **the UI
renamed the domain and lost meaning doing it.**

`morphSettings.ts` names the classes `arrive`, `depart`, `glide`. The panel renders
them ENTERING, LEAVING, MOVING. Two of the three are harmless synonyms. The third is
a lie you can falsify in one edit: `prepareSceneMorphTopology` puts a cell in `changed`
if *anything* differs — colour, opacity, edge ink, face visibility, size. Recolour one
cube and it lands under MOVING while nothing moves. The domain's own word, `glide`,
never made that claim. The confusion tracks the divergence precisely.

So: restore the ubiquitous language rather than invent a fourth vocabulary. Enter /
update / exit is D3's data-join vocabulary and it does leak, but `arrive` / `depart` /
`glide` is this product's vocabulary, it is already written down, and it is more
accurate than the words on screen. In the product's voice (RAIL, BUILD IN, START DELAY,
CAPTURE VIEW — plain, two words maximum) the labels read ARRIVING, LEAVING, CHANGING,
HELD, with CHANGING as the honest rendering of `glide`.

What breaks: `STUDIO.ANIMATION.md`'s stage model and any spec text using the enter/exit
words must move with it, and a rename is only worth doing once. Do it with the tab
removal, not before.

---

## 5. The unreachable cube

In a 1→2 gap the cube that visibly moves is retained and unchanged, so
`prepareSceneMorphTopology` puts it in no class, `sampleSceneMorph` returns `before`
verbatim for it, and MOVING reads 0. The panel is telling the truth about the cubes
and lying about the picture.

It cannot be resolved by renaming the classes. The class partition is correct: that
cube's own authored state did not change. Renaming MOVING to HELD would make the count
non-zero but would attach a motion control to cubes that are not moving under their
own account, which is a second lie in the opposite direction.

It resolves by **attribution**. Two rules:

1. **Every cube on screen belongs to exactly one row.** Today added + removed +
   changed does not cover retained-unchanged, and an incomplete partition always
   eventually reads as a wrong count. Add HELD as a counted row with no controls of
   its own.
2. **Every visible motion is attributed to exactly one actor.** The displacement in a
   1→2 gap belongs to the arrangement, not to the cube. Name the arrangement, state
   its shift, and "Changing 0 · Held 1 · Arrangement shifts" is true and complete.

The objection to naming the arrangement is that it invents a concept the user never
authored. That objection fails on the evidence in §1: the arrangement is *already*
controlled, by MOVING's easing and steps, invisibly. Naming it does not add a concept.
It surfaces a binding that exists and is currently mis-shelved.

The deeper fix is upstream of the panel: if the alignment were computed over
presence-weighted extent, the recentre would ramp with the arriving cube instead of
stepping ahead of it, complaint 1 would dissolve, and the arrangement would need no
control of its own for the 1→2 case. It would still need one when `grid.format` itself
differs between States, since that tween is authored and is currently borrowing
MOVING's easing. Worth measuring before committing to either.

---

## Preferred model (57 words)

A gap moves three actors: the **subject** (cubes, partitioned arriving / leaving /
changing / held, plus the lattice), the **observer** (the camera), and the
**arrangement** (where the whole set sits). Cutting across all three, one instant —
the switch — flips everything discrete: frame, polarity, projection. One motion per
gap; split a population out only on demand.

## The case against it

1. **Three actors is one more than the user asked for.** They complained about tabs
   and empty controls. Answering with a new top-level concept (the arrangement) risks
   a panel that is conceptually cleaner and practically longer. If presence-weighted
   alignment lands, the arrangement may deserve no row at all in the common case, and
   I would have shipped a permanent concept to fix a transient bug.
2. **"Split on demand" hides capability.** The tabs are bad because they hide state,
   but they do advertise that the three can differ. A single motion spec with a split
   affordance trades a visible-but-confusing surface for an invisible-but-clean one.
   If the affordance is missed, the user concludes entering and leaving *cannot*
   differ, which is a worse error than over-editing.
3. **The rename bets on an untested word.** "Glide" is right in the code and unproven
   in the UI. Replacing a word the user misreads with a word the user has never met is
   still a gamble; only the falsification (recolour a cube, watch it appear under
   MOVING) is solid, and that argues for *any* word other than MOVING, not
   specifically for mine.
4. **The subject/observer axis pays for itself only once the camera has controls.**
   Until a camera move can be authored per gap, promoting the observer to a top-level
   actor describes the architecture rather than the user's task.
