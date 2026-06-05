# Scout: the animation studio's timeline vision gap

Scout report, 2026-08-08. Lens: the vision gap between what the owner's own
design documents promise the Animation Studio is, and what a user standing in
front of `/animation` actually gets after v1 slices 1 to 4.

Read-only pass. Sources: `STUDIO.ANIMATION.md`, `ANIMATION.md`,
`ANIMATION.KNOBS.md` on `feat/animation-studio` (`0dbdf38`), and
`~/.mdx/projects/cubicell-spec-studio-v1.md`. Behavioural claims below were
measured by rendering the shipped studio in a scratch copy of `0dbdf38`, never
in the worktree; the worktree was pristine before and after.

## 1. What the docs promise

The promise is specific, and it is not a keyframe editor. Quoting the owner's
own captures:

**The studio is a timeline that opens around the canvas.**

> "This document captures the product direction after the current grid and
> assembly playback work: a timeline that makes a scene feel alive, and,
> further out, recursive grids." (`STUDIO.ANIMATION.md`, preamble)

> "The canvas should remain the primary authoring surface. The default state
> should show the composition with minimal chrome. The timeline expands from
> the bottom when the user wants temporal control." (Studio UX principles)

> "The timeline should feel like an instrument panel, not a second application
> that hides the work."

> "The timeline should preserve that feeling and behave like a precise,
> tactile instrument that opens around the composition." (North star)

**The timeline is a lane stack, and the first lane is the piece's own motion.**

> "The Stage timeline is a **lane stack**: One asset lane per placed asset. A
> structure lane plays its own state-transition sequence. ... Exactly one
> camera lane." (One lane per asset, one camera lane)

> "Stage / Root Piece / Assembly [──────────────] / Asset lanes / Snowflake
> [──────────────] / Camera (stage, one lane) / view keyframes ◆ ◆ ◆"
> (Stage timeline sketch)

**What must always be on screen is named explicitly, and it is transport.**

> "Progressive disclosure: 1. Always visible: Play, Stop, Loop, playhead,
> time, and current scope."

**The on-ramp is seed from structure, and the point of seeding is that it
plays.**

> "The default on-ramp is **Seed from structure**: creating an animation from
> a structure pre-populates its timeline with that structure's States in
> capture order, **ready to play**." (From structure to animation, emphasis
> added)

**And the anti-pattern is named, so the shape is not open.**

> "Do not begin with a large empty keyframe editor. Cubicell's identity is
> structured composition, so the timeline should understand assembly,
> placements, and cues from the first authoring slice."

> "No generic empty keyframe editor as the front door" (`ANIMATION.KNOBS.md`,
> Anti-catalog)

`ANIMATION.md` supplies the underlying vocabulary and, importantly, already
records the transport surface as built and the dock as not yet a timeline:

> "Transport lives in the editor session. The BottomDock provides play, pause,
> stop, loop, and scrub controls. It is a transport control surface, not a
> timeline authoring surface yet." (Slice one: assembly playback)

**Reading of the promise.** The Animation Studio is a canvas with a playhead
under it. A user seeds an animation from a structure, presses Play, watches the
piece assemble and morph through its captured states, drags the playhead to any
moment, and sees the sequence laid out as ordered cards so the composition is
legible at rest. Everything past that (lanes for several pieces, a camera lane,
cues, recursion) is depth added to that spine. The spine is Play plus a
playhead plus a visible sequence.

## 2. The gap, ranked by what a user sees first

Measured surface at `/animation` on `0dbdf38`, with one animation seeded from a
structure. This is the complete rendered text and the complete interactive
inventory:

```
TEXT:        "AnimationsCreateAnimationRenameDelete"
INTERACTIVE: [button "Create animation", button "Rename Animation", button "Delete Animation"]
HAS-STAGE:   true
CANVAS:      1 render
TRANSPORT:   { playing: false, timeMs: 0, rate: 1, loop: false,
               pieceSource: { animationAssetId: "animation", kind: "snapshot" } }
SNAPSHOT:    2 states, score tracks ["assembly", "state-transition"]
```

**Gap 1. The animation cannot be played. Nothing on the page can start it.**
The studio renders the piece frozen at time zero. `playing` is false, `timeMs`
is zero, and the three buttons on the page are Create, Rename, Delete. There is
no Play, no Stop, no Loop, no playhead, no time readout, no rate. There are also
no keyboard shortcuts: `KeyboardShortcuts` mounts only in the Editor studio, so
the space bar does nothing here either. The docs list Play, Stop, Loop,
playhead, and time as **always visible**; zero of the five shipped. This is the
whole of the owner's reaction in one line: he opened an animation studio and
could not animate.

**Gap 2. The sequence is invisible.** The snapshot on screen holds two states
and a complete score (an assembly track and a state-transition track). None of
it is shown. The studio cannot answer "what is in this animation" or "how long
is it". The docs' first timeline sketch is exactly an ordered row of states with
transitions between them, and the Editor already renders precisely that; the
studio renders none of it.

**Gap 3. The library is a menu, not a way in.** With two seeded animations, the
first one stages and the second is unreachable: the studio binds
`animations.find(has origin snapshot)`, and clicking the second row changes
nothing (measured: bound source stays `alpha` after clicking `beta`). Slice 3's
own spec called this "a minimal **open**/create affordance" (D2); create,
rename, delete and seed all shipped, open did not. The card also floats
permanently over the top-left of the canvas with no way to dismiss it, so the
one thing that is always visible is the file menu, in a product whose stated
principle is "the canvas is the hero" with "very little chrome competing for
attention."

**Gap 4. The studio is unreachable except by typing a URL.** There is no link,
tab, or switcher anywhere in the app pointing at `/animation`; the route exists
only as a row in the studio catalog. A user who did not build this cannot find
it.

**Gap 5. Every animation looks the same in the list.** Rows are plain text
names. This is spec slice 7 and correctly deferred, but it compounds gap 3: with
no thumbnail and no open, the list cannot distinguish two animations by either
picture or effect.

**Gap 6. No timing can be adjusted.** Seeded transitions play at whatever the
source structure carried. Re-timing is spec slice 5, unbuilt.

**Gap 7. No camera of its own.** The stage camera lane, the second of the two
lanes the docs promise, is spec slice 6, unbuilt.

### Why the gap exists

The v1 spec is faithful to its own scope and simply never contained a timeline.
Its seven slices are: pool retention, snapshot and seed, studio mount, snapshot
playback, inspector seam, stage camera lane, poster polish. Slice 3's
deliverable is "a minimal open/create affordance listing the project's
animations ... No Browser, no tabs". Slice 4's Done condition is "the snapshot
plays and scrubs through the same transport seam the Editor uses, with proven
sample parity" and it is met, at the seam. No slice ever mounts a control that
lets a person reach that seam. The spec bought the plumbing and never bought the
tap.

### The cheap fact that reframes all of it

**The timeline the owner expected already exists, in the Editor, and the studio
just does not mount it.** `src/panels/BottomDock.tsx` hosts
`PieceMotionPanel`, which is a transport row (Play/Pause, Stop, Loop, a
`TransportPlayhead` range with a time readout and a loop window, and a playback
rate scrub) sitting above `PieceStateStrip`, a filmstrip of state cards with
transition cards between them showing each transition's duration, easing and
order. That is the doc's sketch, built and shipped.

Slice 4 already did the hard half: transport commands act on
`editor.transport`, and the studio's staged scene now resolves through
`transport.pieceSource`, so play, scrub, loop and rate already drive the
snapshot. The merged suite proves it: `tests/animationStudioHost.test.tsx`
scrubs to 100ms and the staged scene changes, sets playing and the frame driver
attaches, and advances to the snapshot's own duration (2400ms against the
structure's 1200ms) where playback stops. The motion is live and correct today.
It is simply unreachable, because no button is on the page.

Two real bindings stand between the existing dock and the studio, both already
named in the spec:

- `usePieceMotionModel` sources its asset from `findAttachedStructureAsset` plus
  `editor.activeStateId`, both Editor-only. Spec slice 5 already commits to
  extracting that "behind a piece-source parameter mirroring the slice 4 seam".
- `PieceMotionPanel` calls `getPieceTransportDurationMs(workbench)` with no
  piece source, so mounted as-is it would show the structure's duration while
  the stage plays the snapshot's. Slice 4 already forked that function to accept
  a piece source; the dock call site is the one place that has not been rebound.

Plus the ordinary mounting cost: the panel needs `EditorCommandProvider` and a
thumbnail renderer, both of which the Editor supplies and the studio does not
yet.

## 3. The minimal timeline

**The smallest scrubbable-timeline increment: mount the existing Piece Motion
dock in the Animation Studio, bound to the open snapshot.** No new timeline is
designed or built. The sequence view and the transport row already exist,
already look right, and already drive the seam that slice 4 landed. The
increment is a binding, not a construction, and it converts a frozen picture
into a moving one.

Its two hard requirements are the two bindings above: the motion model must take
its piece from the studio's snapshot instead of the attached structure, and the
transport duration must come from the snapshot's own score. Choosing which
animation is open (gap 3) rides along, because a dock bound to "the open
animation" forces the studio to have one.

**The user story, one line:**

> As the owner, I open an animation in the Animation Studio and press Play, and
> drag the playhead to any moment, so I can watch the piece move through its
> captured states and stop wherever I want.

## 4. Experiential statements

*What the owner will see and feel on opening the page after each ships. No
implementation language.*

### The minimal timeline

He opens the Animation Studio and the piece is standing there on the black
field, the same composition he sculpted, with a slim bar of controls resting
along the bottom edge and a row of small numbered cards beneath it showing every
state he captured, in order, with the time between each one written on the card
that sits between them. He presses Play. The cubes arrive one after another and
the piece assembles itself, then keeps going, gliding from the first state into
the second while he watches, and comes to rest. He presses it again and takes
hold of the playhead instead, dragging slowly, and the piece follows his hand
exactly, forward and backward, holding still wherever he lets go. He turns on
Loop and leaves it running while he sits back. For the first time the thing he
built is moving in the room he built it for, and the page reads as a studio
because the work is playing and the controls are a thin strip under it rather
than a page of buttons in front of it.

### Slice 5, inspector seam and re-timing

He is watching the loop and the second transition is too fast, the piece snaps
where he wanted it to swell. He clicks the card between the two states. The
right side of the screen fills with that transition's own settings, the same
familiar panel he has always used, and the playhead narrows to loop just that
moment so it repeats in front of him. He drags the duration longer and the
transition immediately stretches under the loop, again and again, until the
swell is right. Nothing else moves: the structure he sculpted this from is
untouched, and this timing belongs to this animation alone. He works the way he
works in the editor, on the piece as it plays, and the animation becomes his
rather than whatever the structure happened to hand him.

### Slice 6, stage camera lane

He scrubs to the moment the piece finishes assembling, orbits the view until the
composition sits the way he wants it seen, and captures it. A small mark appears
on the camera row under the timeline at that moment. He scrubs forward, swings
around to the other side, and captures again. Then he plays from the top. The
view moves on its own now, drifting from the first framing to the second while
the piece morphs beneath it, the whole thing composed as one shot rather than a
model he happens to be looking at. He is no longer previewing an object. He is
watching something he directed, and the page has become the place where the
finished piece is made rather than the place where its parts are stored.

## Source anchors

- Promise: `STUDIO.ANIMATION.md` (North star, Studio today 2026-07-14, Studio
  UX principles, Timeline direction), `ANIMATION.md` (Current implementation
  status), `ANIMATION.KNOBS.md` (Anti-catalog).
- Shipped studio: `src/studios/animation/AnimationStudio.tsx`,
  `src/studios/animation/AnimationLibraryAffordance.tsx`,
  `src/studios/catalogData.ts`.
- The existing timeline: `src/panels/BottomDock.tsx`,
  `src/panels/motion/PieceMotionPanel.tsx` (TransportRow),
  `src/panels/motion/TransportPlayhead.tsx`,
  `src/panels/motion/PieceStateStrip.tsx`,
  `src/panels/motion/usePieceMotionModel.ts`.
- Playback already proven: `tests/animationStudioHost.test.tsx` ("stages a
  seeded snapshot on the shared renderer canvas"), `tests/snapshotPlayback.test.ts`.
- Spec: `~/.mdx/projects/cubicell-spec-studio-v1.md`, slices 3 to 6.
