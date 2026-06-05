# Adversary brief: TRANSITION frame / tab-count proposal

**Seat:** D — adversary  
**Stance:** find what is wrong; do not improve the proposal  
**Sources:** `cubicell-brainstorm-transitions-prior-art.md`, measured defect (align center jolt), panel transcription, screenshot of TRANSITION inspector  
**Constraint:** read-only; cubicell source not re-opened for this brief  

---

## Measured defect (restated, not contested)

`align: "center"` recentres the layout over the destination state's full cell set, including cells at presence 0. On frame one, a pre-existing cube snaps to its final world position before the new cube is visible. Symmetric growth (1→3) shifts nothing; one-sided growth (1→2) displaces by half the added extent (0.75 units in the report). Separately, a retained cube whose authored pose is unchanged belongs to **no** morph class, so no tab owns the motion the user sees.

That second clause is the product failure. The first clause is how the motion is computed. The proposal treats the first and ignores the second.

---

## The proposal under attack

1. FRAME peer of CUBES: SNAP | EASE | HOLD (EASE default; HOLD anchors on retained cubes).  
2. Live counts on CUBES tabs; dim empty tabs.  
3. Contextual sentence explains the frame (e.g. "Frame moves 0.75 on x, carrying 3 cubes.").  
4. Keep ENTERING | LEAVING | MOVING.

---

## Substantive objections

### Objection 1 — Counts decorate the wrong emptiness

**Concrete failure:** User sees a cube jump. They open MOVING, change ORDER / STAGGER / EASING, nothing changes. Proposal adds `MOVING 0` (and dims the tab). The number is *true* under the current class taxonomy and *false* under the user's eyes: something on screen moved.

Counts answer "is this population empty?" The complaint was "I changed every control and the motion I care about did not change." Those are different questions. A badge that says zero while the canvas jolts teaches the author that the UI is lying or that they are looking in the wrong place, without ever saying *where* the right place is. FRAME is a sibling control; the counts stay on CUBES and never point at FRAME.

**Survey precedent:** Silent fallthrough (prior art §2.4 trap 2). Figma dissolves on mis-match with no error; Morph/Magic Move fade; CSS VT drops to root crossfade. Authors "fix Smart Animate" for hours. The survey's honesty fix was **match diagnostics that expose pairing**, not prettier labels on empty buckets. Counts on empty morph tabs are Figma-style silence with a number painted on it.

**Verdict on Q1:** Counts do **not** fix the confusion. They decorate it. They are cosmetic relative to the real failure: a visible motion with no owning control. Worse, they can *amplify* the failure by certifying `MOVING 0` while the only cube on screen translates.

---

### Objection 2 — HOLD is a progressive composition trap

**Concrete failure:** HOLD "anchors on retained cubes so nothing already on screen moves." Grow 1→2 one side, HOLD: origin cube stays put, new cell appears off-centre relative to the old centre. Grow again 2→3 same direction, HOLD again: composition walks further. After a short chain of asymmetric growths the piece sits wherever the **first** state's centre happened to be. The author never chose that as a design position; they chose successive lattice edits. Playback and export leave the figure drifting toward a viewport edge.

Symmetric growth masks the trap (displacement zero). Asymmetric growth is the common case for "add a row / add a wing." HOLD makes the correct-looking first frame of a multi-state film the wrong frame for the last.

**Survey analogues:**

- **Motion layout without a reflow policy** (§1.3, §2.4 trap 3): exit still occupying layout, or survivors jumping late. HOLD is the inverse extreme: survivors never reflow relative to the growing extent, so the "composition" is frozen to early topology.
- **Slide tools with no reframe** (Morph / Magic Move): authors duplicate then edit; the frame of the slide is fixed by the canvas, not by live cell bounds. Cubicell's centre-from-extent is closer to auto-layout than to a slide. HOLD pretends the live lattice has a stable page origin it does not have.
- **Camera HOLD without reframe** (product-adjacent): locking the view while content grows off-sensor is a known failure mode; HOLD copies that onto the layout origin itself.

**When HOLD betrays the author:** any multi-step asymmetric growth, any export of a multi-state sequence where later states should still feel "centred," and any time the retained set is a small subset of the eventual extent (hold on 1 cube while 20 enter around one side).

**EASE default does not rescue HOLD.** Shipping HOLD as a first-class option means someone will pick it for the first jolt, then discover five states later that the film has walked off. Defaults do not erase bad escapes; Morph's visual-similarity default is friendly until large similar sets, then it betrays (§1.7).

---

### Objection 3 — FRAME as three-way control multiplies knobs the survey already rejected

**Concrete failure:** The inspector already has DURATION, SCENE SWITCH, three CUBES tabs each with ORDER (8), STAGGER, EASING (4), STEPS. Proposal adds FRAME SNAP | EASE | HOLD as a peer. Survey synthesis (§2.1–2.2): winning systems ship **one great default** (fade unmatched, interpolate matched) and authors almost never touch enter/exit UI. Figma: ~2–3 knobs total. Morph / Magic Move: 1–2. CSS VT: default crossfade. Nobody ships "frame policy: snap | ease | hold."

SNAP is the bug with a name. Offering SNAP next to EASE legitimises the defect as a style choice. Authors will not know which option matches "don't jolt the cube I already placed"; they will cycle three modes the way they currently cycle three empty tabs.

**Case for zero FRAME controls (Q3):** The frame should simply never snap. Instant recompute of centre from destination cells-at-presence-zero is not a creative option; it is a layout bug. The surveyed systems do not expose "teleport composition origin on transition start." They either keep a fixed canvas (slides) or interpolate layout for survivors (FLIP / Motion `layout`). Zero controls: always ease (or always preserve continuous world positions for subjects that already exist). No SNAP. No HOLD-as-product-surface until multi-step drift is solved with an explicit composition origin the author sets.

---

### Objection 4 — The proposal walks into two named traps at once

**Map to survey traps (§2.4):**

| Trap | How this proposal hits it |
|------|---------------------------|
| **Identity is the product** | Unchanged retained cubes still have no morph identity. FRAME is a global channel; it does not assign those cubes to a class. Wrong taxonomy remains: three tabs, four behaviours (enter, leave, move, **jolt-without-class**). |
| **Silent fallthrough** | Counts + dimmed tabs make empty morph policies look intentional. The jolt is still explained only if the author reads a new FRAME sentence and understands "frame" = layout centre of ghost cells. Mis-match remains quiet if FRAME is left on SNAP (default today, renamed). |
| **Exit coupled with survivor reflow** | The jolt is survivor reflow caused by destination extent including zero-presence cells. FRAME EASE animates that reflow; FRAME HOLD freezes it; neither separates "leaver/enterer presence" from "where survivors should sit." Coupling is renamed, not broken. |

**What it repeats most cleanly:** silent fallthrough dressed as UI completeness. Add a control, add counts, keep the taxonomy that left the jolting subject outside every tab. Same shape as Figma's "Smart Animate is broken" when the real bug is matching: the UI grows while the missing concept (owner of continuous subjects under layout change) stays missing.

---

### Objection 5 — The unexamined shared assumption

**Assumption everyone has been sharing:**  
That layout recentring (`align: "center"` over the destination cell set) is a **frame / composition** problem, orthogonal to the **CUBES** morph classes, and that the fix is therefore a fourth control (FRAME) beside the three tabs.

**Attack:** The displacement is applied as a **world-pose change on retained cubes**. The user experiences a cube moving. Calling that "the frame" is product language for a pose delta the engine already applies to subjects. The taxonomy ENTERING | LEAVING | MOVING pretends only pose-authored morphs are "cube motion," while extent-driven recentring is "not cube motion." That split is false on the canvas and true only in the data model. As long as the discussion accepts the split, every fix will either:

- paper over pose with a sibling FRAME control (this proposal), or  
- leave retained-unchanged cubes classless (status quo),

and never admit a fourth population: **subjects that keep identity and authored local pose but whose world pose changes because the layout origin moved.**

Nobody has questioned whether **MOVING** should include layout-induced pose change, or whether centre should be computed only over **positive-presence** cells (or over the intersection of states), or whether `align: "center"` during a transition should be forbidden from reading destination zeros. Those are classification and layout-input questions. FRAME SNAP|EASE|HOLD assumes the classification is fine and only the interpolation of an abstract "frame" needs productizing.

**Secondary unexamined assumption:** that the author wants a *policy choice* at all. Survey defaults suggest they want the jolt gone, not three ways to schedule it.

---

## Direct answers (required)

### 1. Do counts on tabs fix the confusion, or merely decorate it?

**Decorate it.** The user's failure was: visible motion, no owning control. Counts report empty morph populations under a taxonomy that excludes the jolting subject. They do not assign ownership. They can make the UI look more "correct" while the canvas still contradicts `MOVING 0`. Cosmetic unless paired with a class that actually owns the motion (which this proposal refuses by keeping three tabs and parking the motion on FRAME).

### 2. HOLD is a trap, is it not?

**Yes.** Anchoring on retained cubes freezes composition origin to early topology; asymmetric growth chains drift the piece off-centre. Analogues: Motion layout/reflow coupling extremes; slide tools where canvas origin is fixed while content intent is not; camera hold without reframe. HOLD betrays on multi-step one-sided growth and on export of sequences that should stay optically centred.

### 3. Three or four options is already too many. Is FRAME a control at all?

**FRAME should not be a three-way control.** Case for zero: never snap; continuous world positions for already-present subjects; no SNAP option that reifies the bug; no HOLD until an authored composition origin exists. Survey winners: one default, rare escape hatch, not a peer strip of three frame policies next to an already dense CUBES stack.

### 4. What does this proposal repeat?

Primarily **silent fallthrough** (honest-looking empty tabs + optional FRAME the author may never open) and **exit/survivor reflow coupling** renamed as frame policy. Secondarily it refuses the **identity** trap's lesson: the jolting cube still has no identity in the morph model.

### 5. The one thing nobody has questioned

That the jolt is a **frame** problem rather than a **class / layout-input** problem: retained subjects undergoing world-pose change from centre recompute are treated as outside CUBES by definition. Challenge that split; the proposal collapses.

---

## Additional concrete failure modes (minimum three satisfied above; extras)

6. **Sentence as excuse:** "Frame moves 0.75 on x, carrying 3 cubes" narrates the bug in prose. Authors who do not speak "frame" still only have CUBES tabs to twist. Copy is not a control surface.

7. **EASE default still fights ENTERING choreography:** If the whole lattice eases centre while ENTERING runs MADE + stagger, survivors and newcomers share one global translation on top of local enter recipes. That is a second silent coupling: frame ease × enter stagger. Motion's good pattern is layout on survivors **and** independent presence on enter/exit, with an explicit mode (`popLayout`), not a global frame fader.

8. **Dim empty tabs reduce discoverability of the only remaining knob:** If LEAVING and MOVING are dim, attention stays on ENTERING. FRAME sits outside CUBES; dimming increases the chance FRAME is never found when the jolt happens with ENTERING non-empty (exactly the 1→2 case: enterers exist, movers class-empty, jolt on retained).

---

## One change (only after objections)

**Delete SNAP as a concept and delete FRAME as a three-way peer control.** Compute transition layout centre only from cells that have positive presence in the **origin** state (or from the intersection of present subjects), and interpolate any centre change continuously over the transition duration with **no user-facing FRAME mode**. Put layout-induced pose change for retained subjects into the morph model the user already stares at (own them under MOVING, or rename the strip so "no tab" cannot describe a moving cube). Counts then report a non-zero owner for the motion the eye already sees.

That is one change with two inseparable parts: **stop reading presence-0 destination cells into the transition origin**, and **never leave a moving cube outside every tab**. Everything else in the proposal (HOLD, SNAP, FRAME strip, sentence-as-fix) is load-bearing decoration on the wrong abstraction.

---

*End of adversary brief.*
