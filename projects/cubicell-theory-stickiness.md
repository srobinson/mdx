# Cubicell Theory, Lens 4: Stickiness

Seat 4 of 4. Fresh eyes, no renderer time. Grounded in PRODUCT.md, CUBICELL.md,
PROJECT.EXPORT.md, STORAGE.md, `src/export/streamRecorder.ts`, and the state
capture surface. I did not run the app; every timing claim below is inferred
from the command surface and is marked unverified. This lens answers one
question honestly: why would somebody open this twice?

## The one structural asset

Before the five questions, the asset they all lean on. Cubicell's confinement
is a taste guarantee. Unlit flat cubes, minimum edge thickness, black and white
polarity: the worst scene a beginner can make still looks designed. Most
creative tools have an ugly novice phase (a first Blender render is
embarrassing; a first cubicell lattice is a competent print). A high aesthetic
floor is the rarest stickiness property a tool can have, and cubicell has it by
construction. Everything below is about whether the product converts that floor
into a reason to return.

## 1. The first thing worth showing another person

Today the fastest path to a show-worthy piece is a small occupancy pattern,
two captured states, and Play: the lattice reshapes while the camera swings
between the two authored poses, because the camera is part of the state. That
is genuinely postable output; the morph plus camera move reads as intentional
motion design even when the author had no plan.

Estimated time: 10 to 20 minutes including orientation, unverified. The
capture-state-then-play loop is short; the orientation cost is discovering
that states are the animation primitive at all.

The honest caveat: that first piece is handsome but anonymous. It is a cube
morph, and it is nobody's cube morph. The documented text direction (spell a
word, collapse it, reassemble it) is the moment the first artifact becomes
"mine" rather than "the tool's", and it is not on main. Until a newcomer can
put something of themselves into the lattice, the first session produces a
demo of cubicell rather than a piece by the newcomer.

## 2. Mastery and the ladder

Mastery here is performance: a multi-state score, selection queries driving
staggered part animation (edge pulses radiating from a chosen cube, faces
dropping in wave order), camera choreography authored per state, delivered at
VJ tempo. The reference class is Ikeda-adjacent geometric motion synced to
rhythm. The one-command-vocabulary decision means the ladder is structurally
real: the keypad tap a beginner makes and the pattern a master performs are
the same words at different depth. Nothing is unlearned on the way up.

But the ladder is invisible. There is no example piece, no gallery, nothing in
the product that shows what ten hours of skill buys. A newcomer who makes the
two-state morph has no way to see that a master's piece even exists, let alone
that it was made from the same commands they just used. Worse, the confinement
flattens perceived difficulty from the outside: a masterful piece and a lucky
one look like siblings to an untrained eye, the same way pixel art hides its
skill gradient from non-practitioners. Connoisseurship of cubicell pieces will
have to be taught by exposure, and the product currently provides none.

## 3. The artefact that leaves

Two things leave the tool today: project JSON and a live tab-capture WebM
(`streamRecorder.ts`, getDisplayMedia plus MediaRecorder). Deterministic
fixed-step export is a proposed document, not shipped code.

The identity question has a strong answer. The look is the watermark. Flat
unlit cubes with constant screen-thickness edges in strict black and white are
recognizable at thumbnail size in a feed, with no logo needed. Because the
camera is authored per state, every piece leaves as a film rather than a
model: self-contained, composed, viewable with zero context. That is exactly
the artefact shape that carries identity to people who never used the tool.

The mechanics undercut it. A screen-grab WebM is the lossy version of a look
whose entire value is precision: hard black-white boundaries are where codec
ringing shows first, and capture is realtime rather than frame-exact. The
signature aesthetic deserves the deterministic exporter that only exists as a
proposal. And the artefact is a dead end: no attribution, no link, no way for
a viewer to open, remix, or even find the tool. Project JSON is an exchange
format with no one to exchange with.

## 4. Who this is for

Specific enough to be wrong: a designer or creative technologist, mid-20s to
40s, who owns After Effects but posts geometric loops to X or Instagram, keeps
a Vera Molnár or Ryoji Ikeda reference folder, probably makes or performs
music, and wants a daily-postable practice where the tool enforces taste so
volume stays high. The monome crowd; people who buy grid controllers. They
return to instruments, and cubicell is shaped like one.

Who it is not for: 3D generalists (the confinement reads as missing features
within minutes), casual users (no meaningful artifact inside the first
session today), and data-viz people (no data path, correctly). The second
documented user, an LLM driver, has no retention to leak and is out of scope
for this lens.

## 5. Where retention leaks

Leaks named, fixes withheld per brief.

1. **The dead-end artefact.** The finished piece leaves as anonymous lossy
   pixels with no route back to the tool or the maker. For this user, the
   engine of return is make, post, response, make again; the loop breaks at
   the exact point where it should compound.
2. **The anonymous first session.** Blank lattice start plus an abstract-only
   composition language means the first artifact requires borrowed taste to
   feel owned. The word path that would make session one personal is
   documented and unshipped.
3. **The invisible ladder.** No in-product exposure to advanced pieces. The
   shared command vocabulary built a real ladder and then hid it.
4. **Nothing calls you back.** Single-user localStorage world: the only
   return motive is the maker's own unfinished piece, and export ends that
   pull. No audience, no occasion, no incoming pieces to answer. VJ tempo
   implies a performance occasion the product cannot yet supply.
5. **No object of exchange.** Pieces cannot be received, opened, or remixed,
   so there is no maker-to-maker circulation. Every comparable aesthetic
   niche (pixel art, tracker music, shader demos) retains through circulating
   artifacts that reopen in the tool.

The biggest is leak 1. Leaks 2 through 5 shrink the pool; leak 1 wastes the
users the product has already won at their moment of maximum motivation.

## Coda: what THEORY.md is actually pointing at

THEORY.md is a transcript of Richard Behiel's spinor video: SO(3) is not
simply connected, rotation loops fall into two homotopy classes, and spinors
live on the double cover, flipping sign after 360 degrees and restoring after
720. Nobody states the cubicell connection, so here is the stickiness reading:
cubicell already owns exact rotation steps and a two-valued polarity. A piece
whose full 360 rotation returns home with black and white inverted, requiring
a second full turn to restore, is a spinor made visible, native to this
exact primitive set and to nothing else on the market. Signature motifs are
how confined tools become recognizable schools rather than feature lists;
this one is sitting in the repo disguised as a physics transcript.

## Verdict

The aesthetic floor and the film-shaped artefact are elite stickiness raw
material. The product currently spends them on a loop that terminates: a
beautiful anonymous piece, degraded in export, leaving through a door with no
handle on the outside.
