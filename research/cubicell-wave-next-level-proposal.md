---
title: Cubicell Wave, from a track to an instrument
type: research
tags: [cubicell, animation, wavetrack, sine, modulators, vj, controls, proposal]
summary: The shipped WaveTrack proves the ontology fits but reads as one look per order; both agents converge on replacing it with a Move stack (driver, discriminated source, envelope, amount, channel output) over shared kernels, shipped in four slices from a useful offset Move to live recordable input, with a full wire reset.
status: active
project: cubicell
confidence: high
related: [cubicell-turn-tests-salvage]
created: 2026-09-03
updated: 2026-09-03
---

# Cubicell Wave, from a track to an instrument

Joint brainstorm between the two feat/wave-track agents at Stuart's request
after PR #222. Sections marked with an author are that agent's position;
the recommendation at the end is the converged one.

Ground truth referenced: `src/domain/waveTrack.ts`, `src/evaluation/waveAt.ts`,
`ANIMATION.md` (Waves), `ANIMATION.KNOBS.md`, `STUDIO.ANIMATION.md` (UX
principles, progressive disclosure), `docs/superpowers/specs/2026-07-11-vj-performance-design.md`,
and the cm ideation entry `01a050ba` (2026-08-30 sine direction).

## Recommendation in one screen

Replace the single `WaveTrack` with a **Move stack** on the piece score. A
Move is one modulation: a driver (piece clock, beat, trigger, none), a
discriminated source (ranked field plus signal; sampled noise or media;
controlled pointer, audio, MIDI), an envelope over field value, an amount in
[0, 1], and an output discriminated by channel (offset, scale, part opacity,
palette flip, rotation). Fields return a value and, where they have one, a
gradient. Every Move samples one immutable base pose; outputs fold by a fixed
per-channel algebra. Presets are the front door: Ripple, Lift, Steps, Jitter,
Breathe first. A wire reset is accepted; nothing persisted needs to survive.

Four slices, each proven live on a line, a plate, and a volume:

1. **Move library and kernel.** Replaces `WaveTrack`. Ranked sources, oscillator
   and step signals, envelope, offset and scale outputs, five presets, Move
   card with a live strip, Phase view, Advanced disclosure.
2. **Stack and canvas authorship.** N Moves with ids, mute, solo, explicit
   reorder; direct field handles on the canvas; Motion Brush; part opacity,
   palette flip, and a measured ordered-rotation prototype (Tumble).
3. **Living sources.** Seeded 4D noise (Living Surface); media luminance spike
   and Display only if sampling never blocks the frame; Orbit from gradients.
4. **Live and recordable.** Pointer (Touch), beat clock, triggers, audio and
   MIDI drivers, intensity master, gesture recording, fixed-step replay,
   kernels shared with the Performance rig.

Details: section 9. History of how we got there: sections 2 to 8.

## 1. Where we are

PR #222 ships `WaveTrack`: one sine over the cell offset channel.

    value = amplitude * sin(2π (cycles * t/duration + phase - spread * rank))

- Four numbers plus an axis and an `AssemblyOrder`: amplitude (world units),
  cycles (whole, per piece duration), phase (turns), spread (turns of travel
  from nearest to furthest cube).
- Rank is a continuous spatial field sharing `assemblyOrderMetric` with the
  build order, normalized over the piece's stable cell union, sampled at each
  cube's live lattice position. Whole cycles make looped playback seamless.
- One wave per channel. Authored from a WAVE pane: switch, Order, Axis, Amp,
  Cycles, Travel, Phase. A committed edit plays the piece.

What the screenshot shows (12x12 plate, order Dice, axis Z, amp 0.15,
cycles 1, travel 2): every cube at a random phase along Z reads as jitter,
and the expected wavefront disappears. The evaluator is correct. The control
combination produces the wrong instrument. The observation generalizes: a
single smooth sine with equal weight on every cube has exactly one look per
order. The gap is between "a wave" and "an instrument".

## 2. Diagnosis (Fable)

Why the current controls are not yet useful, in order of leverage.

1. **No shape.** Sine only, always smooth. Cubicell's identity is quantized,
   mechanical, stop-motion (see `quantize` on `ClassMotion` and
   `AssemblyTrack`, "strongly on brand" in KNOBS). A wave that snaps to N
   steps, or a square wave that flips cubes between two heights, reads as
   Cubicell; a floating sine reads as a generic demo.
2. **No locality.** The field has infinite extent: every cube moves with the
   same amplitude. A ripple that dies out, a scanning band, a wave that only
   lives in the outer shell all need a falloff or a window over rank. Reference
   ranks occupy [0, 1], while live geometric samples may extrapolate. A rank
   mask adds one scalar gain without a new spatial coordinate system.
3. **One channel, one axis.** Offset along one grid axis. Breathe (scale),
   pulse (edge weight), shimmer (face opacity), and the shell-state flip are
   all listed `[near]` in KNOBS and all read in the unlit, flat-palette
   renderer, where curvature never will (memory: form is authored geometry).
4. **No layering.** One wave per channel forbids the thing that makes sine
   interesting: interference. Two radial sources from two cubes, or a slow
   breathe under a fast ripple, are the difference between a screensaver
   and a composition. Offsets add; the Moment already supports it.
5. **Travel only outward.** `spread` is clamped to [0, 2]. A negative spread
   is an inward-travelling wave, a one-line win. Whole-number spread is a
   legitimate look (nearest and furthest in phase) and should be reachable
   from the UI as such.
6. **Coupled to piece duration.** Cycles per piece keeps loops seamless but
   ties rate to duration. The approved VJ design wants a beat clock with
   phase derived from a stamped beat. The wave needs a clock seam. BPM belongs
   to the Performance context.
7. **No intensity.** The VJ invariant says every modifier exposes an
   intensity in [0, 1]: scrub it for a reveal, loop it for animation, bind
   it for performance. The wave has amplitude but no master, so nothing to
   bind, mute, or fade.
8. **Numbers, no picture.** The pane is six numbers. Nothing shows the shape
   of the wave, where its origin is, or how far it travels. Motion shows
   itself in motion, and the commit-plays rule helps, but a static glyph of
   the waveform and travel direction would make the six numbers legible.
9. **Random order is a different instrument.** Dice as a wave phase is a
   per-cube jitter. It is useful (KNOBS "scatter") and should be named Jitter,
   with seed, hold time, and quantize. Travel should remain a spatial control.

## 3. Design space, ranked (Fable)

### A. Shape the oscillator [now-ish, additive]

- `waveform: "sine" | "triangle" | "saw" | "pulse"`, with duty on the pulse
  variant. A square is a pulse at 0.5 duty. All shapes are periodic in turns,
  so `cycles`, `phase`, and `spread` keep their meaning.
- `quantize?: number` steps on the [-1, 1] value. Reuses the on-brand
  mechanical feel and the existing quantize idiom.
- `polarity: "bipolar" | "positive"`. Positive maps the signal to [0, 1], so
  cubes only rise from home. That builds a floor breathe or pressed-key look.
- Exclude `EasingId`. `settle` overshoots above 1, and an eased half-cycle
  introduces a second shape system beside waveform and quantize.

### B. Localize the field [now-ish, additive]

- `window?: { center: number; halfWidth: number; feather: number }` in rank
  space. Cubes outside the window are still. This is a static mask. A moving
  scan needs an explicit envelope position and clock.
- `falloff?: "linear" | "smooth"` scales amplitude by rank so a ripple dies
  out or grows. Absence means full strength.
- Negative `spread` for inward travel (drop the 0 floor).

### C. More channels [near, ordered by render cost]

1. Scale, uniform and per axis. Rendering is cheap, but `Moment` needs a
   separate per-cube scale multiplier. Presence must keep ownership of
   arrival and departure.
2. Part opacity. Cube parts and instance attributes already carry opacity,
   but `Moment.partColors` carries color tweens only. Add a separate sparse
   opacity multiplier. Binary flips fit the identity better than fades.
3. Edge weight: thickness feeds edge junction resolution, so animating it
   re-resolves junctions per frame. Prototype and measure before promising.
4. Presence stays with assembly and the State morph (invariant 3).

### D. Layer waves [near]

- N waves per piece, each with an id, `channel`, and `mute`. Offsets add,
  scales multiply, opacities multiply, matching the VJ composition rules.
- Document operations become `add-piece-wave`, `patch-piece-wave`, and
  `remove-piece-wave`. Add `move-piece-wave` only when evaluation order has
  authored meaning. The pane becomes a short list of wave cards with one
  expanded, the same idiom as the state strip.
- Two radial waves from two cube origins create interference through the
  existing cube-origin and additive-offset rules.

### E. Clock seam and intensity [later, depends on Performance context]

- Keep `cycles` per piece for the score (seamless loop is the score's
  contract). Add a `clock: "piece" | "beat"` discriminator only when the
  Performance clock exists; in beat mode cycles means cycles per bar.
- `intensity` [0, 1] master on the wave list, session-side for performance,
  authored as a default in the document. Bindable through the existing
  control-binding table when the perform lane lands.
- Share the scalar kernels: `sampleOscillator(phaseTurns, shape) -> value`
  and `sampleEnvelope(rank, envelope) -> gain`. Score and Performance keep
  separate clock and addressing adapters. The Performance modifier shares
  these kernels.

### F. Presets and the picture [now-ish, UI only]

- Slice 1 code presets: Ripple (radial sine), Lift (positive radial), Steps
  (quantized sweep), and Jitter (Dice pulse). Add Breathe with scale, Scan
  with a moving envelope, and Keys with part opacity in their owning slices.
- One inline field strip in the pane: 24 samples over normalized rank at the
  current phase. It shows waveform, envelope, polarity, and travel direction
  together. A generic one-cycle glyph cannot explain locality or Dice.
- Progressive disclosure per STUDIO.ANIMATION: default row shows Channel,
  Shape, Amp, Cycles, Travel; Advanced reveals Phase, Quantize, Window,
  Polarity, Duty, Falloff, and Origin.

### G. Out of scope here

- Sine as a form generator (fill cells where y = round(A sin(kx + φ))) belongs
  to scene operations. It deserves its own slice.
- Camera sway belongs on the stage score.

## 4. Partner section (Codex)

I agree with the order of work: make one wave useful, then layer channels,
then connect it to Performance. I would change the model and the product test.

### Start from named looks

A larger control set can still be a poor instrument. Slice 1 should open with
four curated looks on the current offset channel: Ripple, Lift, Steps, and
Jitter. Selecting one writes ordinary Wave values. The author can then tune
the result.

This gives every new parameter a visual reason to exist. It also gives the
team a concrete acceptance test. Each look must read clearly on a line, a
plate, and a volume. Dice must be named Jitter in the preset because it is a
random phase field. Travel remains a spatial control.

Move the code presets into Slice 1. Saved presets can wait for Performance or
evidence that users need a personal library.

### Keep four concerns separate

A useful wave has four independent parts:

1. The spatial field maps each cube to rank. `AssemblyOrder` already owns this
   calculation, including a picked cube origin.
2. The oscillator maps temporal and spatial phase to a scalar signal.
3. The envelope maps rank to gain. A static window and falloff belong here.
4. The output maps the signal onto a channel.

The evaluator should make that composition literal:

    phaseTurns = cycles * progress + phase - spread * rank
    signal = sampleOscillator(phaseTurns, waveform)
    gain = sampleEnvelope(rank, envelope)
    value = signal * gain

A moving scan is a fifth concern because its envelope position changes with a
clock. Keep it out of the static window contract. Add it later as an explicit
moving-envelope mode.

### Choose the structured track

There are three credible domain shapes.

| Shape | Strength | Cost | Verdict |
| --- | --- | --- | --- |
| Add optional fields to the current flat `WaveTrack` | Small first diff | Channel-specific fields create invalid combinations | Short-lived |
| Structure `WaveTrack` as field, oscillator, envelope, and discriminated output | Each part has one job; channels remain type-safe | One coordinated wire reset | Recommended |
| General `PropertyTrack` or assignable LFO | Maximum reuse | Premature abstraction; conflicts with the separate Performance context | Defer |

Cubicell has no external users. Use that freedom now. A structured track keeps
future channel states legal:

    type WaveOutput =
      | { channel: "offset"; amplitude: number; axis: GridAxisName }
      | { channel: "scale"; amount: number; axes: ScaleAxes }
      | { channel: "part-opacity"; amount: number; target: PartTarget }

Keep `axis` and `target` inside the output variants that own them. Coordinate
the record and storage reset when this shape lands.

### Extend `Moment` by channel

`Moment` currently has `displacement`, `presence`, and color-only
`partColors`. Scale and opacity need their own sparse overlays. Presence must
remain the authority for arrival and departure because staging removes cubes
at presence zero.

Compose outputs at one boundary:

- Offset vectors add.
- Scale multipliers multiply and clamp to the channel's positive range.
- Part opacity multiplies and clamps to [0, 1].
- Presence keeps its existing minimum rule and cannot be authored by a wave.

This boundary should guard non-finite values. The rule then works for Score
and the future `PerformMoment`.

### Make layering cheap to understand

Give every wave an id before multiple waves land. Remove the rule that allows
only one wave per channel in Slice 2. Add, patch, remove, and mute are enough
while channel composition is commutative. Stable array order keeps the list
calm. Reordering can wait until an operator makes order observable.

Picked cube origins fit a piece score because the structure owns stable cube
ids. The Performance rig remains structure-agnostic by contract, so its field
adapter must use bounds and patterns. Share only oscillator and envelope math.
Keep the addressing schemas separate.

### Show the field the cubes receive

The pane should label `AssemblyOrder` as **Field** and the displacement axis as
**Move**. The current labels, **Order** and **Axis**, hide that distinction.
Expose the picked origin as a visible control. Changing the order captures it
implicitly today.

Use one live field strip with samples across rank at the published playhead.
The strip should show the combined oscillator and envelope. Mark the origin
and travel direction. Preset, Channel, Shape, Amount, Field, Move, and Travel
stay visible. Phase, duty, quantize, polarity, window, falloff, and origin live
in Advanced.

### Prove the looks

Each slice needs the existing contract, browser, build, and delivery checks.
Add a visual acceptance matrix for the feature itself:

- Ripple reads as a coherent front on a plate and a volume.
- Lift never crosses below the authored pose.
- Steps produces stable mechanical levels at fixed playhead samples.
- Jitter is deterministic for one seed and changes only when rerolled.
- Two layers compose by the declared channel rule.

Profile a 12 by 12 plate and a 20 by 20 by 20 volume. Keep allocation out of
the inner cube-by-layer loop, as the VJ design requires.

## 5. First converged draft (superseded)

The first convergence assumed persisted data and existing documents were
constraints. Stuart lifted both. Section 9 supersedes it.

## 6. Open questions, first round (superseded)

Folded into section 9.

## 7. Open book (Fable)

Stuart's brief widened after section 6: no persisted data needs preserving,
and no existing document constrains the design. This section thinks from
first principles about what the capability is, then re-cuts the slices.

### The capability is modulation, and the wave is one voice of it

A sine on offset is one point in a space with four axes:

    signal  x  field  x  channel  x  time source

- **Signal**: what varies. Sine, triangle, saw, pulse; coherent noise (a
  slowly evolving 3D noise field, the single most valuable addition, because
  it makes a lattice breathe like a living surface instead of a machine);
  a step sequencer (N discrete levels per beat bucket, the Cubicell look);
  an envelope (attack, hold, release, fired by a trigger); a hand-drawn
  curve; later audio bands and MIDI CC.
- **Field**: where it lands. Today: `AssemblyOrder` ranks (radial, shell,
  spiral, sweep, dice). Open book adds true 3D fields: plane, sphere, box
  with falloff; the noise field itself as a field; **an image or video
  sampled onto the lattice** so luminance becomes rank. The face media
  library already holds images and videos. A plate driven by a video's
  luminance is a low-resolution physical display made of cubes, and the
  screenshot is already a heightmap waiting for a source. Also the
  **pointer**: the canvas is the control (memory), so the cursor is a field
  origin and a wave follows the hand.
- **Channel**: what changes. Offset (any axis, or along the field's own
  gradient), rotation (quantized 90 degree tumbles are the most Cubicell
  motion nobody has yet), scale, part opacity, edge weight, palette flip
  (the two-value palette means a "color" channel is a binary swap, which is
  a strength), gap and cell size at grid level.
- **Time source**: the piece clock (loop seamless), a beat clock (Performance),
  a trigger (one shot, envelope), or the pointer (no clock at all).

Every cell of that space is a pure function of (cell context, time) into the
Moment, serializable, undoable, exportable. That is why it fits: the
ontology already forces the right shape.

### What that makes possible that a wave cannot

- A plate that shows a video in cube heights, then a wave passes over it.
- A logo reveal where cubes tumble into place by shell (rotation channel,
  shell field, envelope signal, triggered).
- A hover ripple on a hero: pointer field, sine signal, offset channel, no
  clock.
- A step sequencer on edge weight synced to beats: the VJ moment.
- Two noise fields at different rates on offset and opacity, so the surface
  never repeats but stays calm.

### Model: a modulator stack replaces the single WaveTrack

    type Modulator = {
      id: string;
      enabled: boolean;
      amount: number;                       // the [0,1] intensity master
      field: Field;                         // order | plane | sphere | box | noise | media | pointer
      signal: Signal;                       // oscillator | noise | steps | envelope | curve
      envelope?: RankEnvelope;              // static window and falloff over the field value
      output: Output;                       // discriminated by channel
      clock: "piece" | "beat" | "trigger" | "none";
    }

The piece score holds an ordered `modulators: Modulator[]`. Composition per
channel is fixed and total: offsets add, scale and opacity multiply, rotation
adds in quarter turns, presence is never a modulator target. `WaveTrack`
becomes `{ field: order, signal: oscillator, output: offset }` and needs no
compatibility path: Stuart has released us from it.

### Authoring that matches the model

- A modulator card: Preset, then Signal, Field, Channel, Amount, Travel on
  one row, with a live field strip. Advanced holds phase, duty, quantize,
  window, falloff, origin, seed.
- Direct manipulation on the canvas: drag the field origin; scrub amount on
  a cube; for media fields, the media picker already exists.
- Presets as the front door (partner's point, adopted): Ripple, Lift, Steps,
  Jitter, Breathe, Tumble, Scan, Display (media), Touch (pointer).
- Solo and mute per card; the stack is the piece's kinetic layer, drawn as
  one lane in the piece timeline.

### Cost and order of work, honestly

Cheap: oscillator shapes, quantize, polarity, envelope, signed spread,
scale and opacity channels, presets, the strip. Medium: noise signal and
noise field (one 3D simplex implementation, deterministic by seed), plane
and sphere fields, rotation channel (quantized, so it is a cheap pose
change), the stack with add/patch/remove/mute. Larger: media field (sample
luminance onto lattice per frame from the existing video texture path),
pointer field (needs the canvas hit surface as a field origin), edge weight
(junction re-resolve), beat clock and triggers (Performance context).

### Re-cut slices

1. **Modulator model and offset voices.** Land the `Modulator` type with
   field = order, signals oscillator and steps, envelope, output offset; wire
   reset; presets Ripple, Lift, Steps, Jitter; card with strip and Advanced.
2. **Channels and stack.** Scale, part opacity, rotation outputs; N modulators
   with mute and solo; composition boundary in the Moment; Breathe and Tumble
   presets.
3. **Fields and noise.** Noise signal and field, plane and sphere fields,
   media field. Display preset. This is the slice that makes the lattice a
   surface rather than a machine.
4. **Instrument.** Pointer field, beat clock, triggers with envelopes,
   intensity bound to controls, shared kernels with the Performance rig.

## 8. Open-book partner pass (Codex)

The modulation engine is the right foundation. The product should say
**Move**. A person chooses Ripple, Tumble, Display, or Touch and works on the
canvas. Advanced controls can reveal the underlying source, field, driver,
and output when that vocabulary becomes useful.

### Three product shapes

| Shape | Strength | Cost | Decision |
| --- | --- | --- | --- |
| Raw modulator matrix | Exposes every combination | Makes empty or meaningless combinations easy and asks the user to design a signal graph | Keep inside Advanced |
| Tailored Move cards | Starts from a visible intention and shows only relevant controls | Needs a small schema for each Move family | Use as the primary experience |
| Node graph | Supports arbitrary routing and reuse | Creates a second application inside Cubicell | Defer |

The first useful result should take three actions or fewer: add a Move, choose
a preset, and drag one canvas control. The default stack should already make a
quiet, coherent composition.

### Model sources honestly

`signal × field` describes separable sources such as a sine wave traveling
through assembly order. Evolving noise, video, and pointer input are
space-time sources. Their value depends on the cell and time together.
Representing them as two independent selectors would make the type promise
more freedom than the implementation can support.

A general evaluation pipeline can remain small:

```text
driver -> source(cell, resolvedTime, inputs) -> envelope -> amount -> output
```

Use a discriminated source union:

```ts
type ModulationSource =
  | { kind: "ranked"; field: Field; signal: Signal }
  | { kind: "sampled"; sampler: "noise" | "media" }
  | {
      kind: "controlled"
      controller: "pointer" | "audio" | "midi"
      field: Field
    }
```

This keeps invalid combinations out of authored state. The runtime resolves
drivers and live inputs separately from the serializable Move definition.

Fields should also return spatial direction when they have one:

```ts
type FieldSample = {
  value: number
  gradient?: Vec3
}
```

The scalar drives amount. The gradient enables expansion from a sphere,
travel along a plane, and spiral flow around an origin. Those effects fit the
lattice better than moving every cube along one global axis. Media and noise
may omit the gradient or derive an approximate one.

### Make evaluation stable

Every Move should sample the same immutable base context. That context should
contain the document pose plus the resolved state morph. Move outputs then
fold into a final render pose. A later Move should never sample an earlier
Move's result. This rule prevents accidental feedback and makes reorder
behavior explainable.

Composition needs channel-specific algebra:

- Offset adds.
- Scale and opacity multiply.
- Palette flip uses parity, so multiple flips compose predictably.
- Rotations fold in stack order as quarter-turn quaternions. Rotations around
  different axes do not commute, even when every angle is quantized. Reorder
  must therefore remain an explicit semantic operation.
- Grid gap and cell size belong to a separate grid modifier phase. Fields
  sample the base grid before those modifiers run, avoiding coordinate
  feedback.

Rotation may invalidate exposed faces, junctions, or edge work. Measure the
actual downstream cost before classifying it as cheap. The first rotation
prototype should use the canonical line, plate, and volume fixtures and
inspect resolved geometry as well as frame time.

### Put authorship on the canvas

The largest opportunity is a visible field editor:

- **Phase view** tints cells by field value and draws optional gradient
  arrows. It makes an invisible Move legible before playback.
- **Direct handles** place the origin, direction, radius, and falloff on the
  lattice. Dragging a sphere origin should feel like moving a light.
- **Motion Brush** paints per-cell weights or records a drawn path as a custom
  field. This gives irregular assemblies an authored rhythm that formulas
  alone cannot produce.
- **Record gesture** captures pointer control events against the piece clock.
  The recorded controller becomes repeatable, editable, and exportable.

Move cards should show one compact preview strip, amount, travel, mute, and
solo. Selecting a card activates its canvas handles and Phase view. Presets
remain editable Move definitions, so a user can begin with Ripple and finish
with something unique without crossing into a separate mode.

### Treat live input as a recording problem

Pointer, audio, and MIDI values are session state. Their configuration is
serializable. The live stream itself becomes durable only when recorded.
Deterministic replay and export therefore require timestamped control events
against a fixed clock. This boundary preserves undo for authored changes and
gives performance an honest route into a saved piece.

### Signature Moves

- **Living Surface** samples seeded four-dimensional coherent noise. It should
  feel continuous in space and time, with no oscillator seam.
- **Display** maps image or video luminance to height, scale, or palette. Avoid
  per-frame CPU pixel readback. Prototype a low-resolution luminance atlas or
  GPU sampling path before committing the feature.
- **Touch** places a pointer field on the lattice and records the gesture.
- **Orbit** uses a radial field gradient and tangent direction to turn a plate
  or volume around a chosen origin.

Display could become a signature capability, but it deserves a technical
spike. Reusing the existing video texture does not prove that cell luminance
samples are available without a pipeline stall.

### Re-cut slices

1. **Move library and kernel.** Add tailored Move cards, ranked sources with
   oscillator and step signals, offset and scale outputs, presets, Phase view,
   and complete reset. Prove a strong result in three actions or fewer.
2. **Spatial authorship and stack.** Add multiple Moves, stable IDs, mute,
   solo, direct field handles, gradient outputs, Motion Brush, and explicit
   composition rules. Prototype ordered rotation here.
3. **Living sources.** Add seeded four-dimensional noise and run the media
   sampling spike. Ship Display only with a non-blocking render path.
4. **Live and recordable.** Add pointer, beat, trigger, audio, and MIDI
   drivers, global intensity, gesture recording, and fixed-step replay.

### Acceptance bar

- A useful animated composition is reachable in three actions or fewer.
- Line, plate, and volume fixtures prove field direction and channel
  composition visually.
- Fixed-step replays produce identical resolved poses for the same document
  and recorded inputs.
- A 12 by 12 plate and a 20 by 20 by 20 volume are profiled with no allocation
  in the per-cell inner loop.
- The authored schema cannot represent unsupported source and channel
  combinations.
- Media sampling performs no blocking per-frame readback.
- A recorded pointer gesture replays identically after reload and export.

## 9. Final converged recommendation

Both agents agree on the following. Where we differed, the resolution is
named.

### Vocabulary

The product says **Move**. The engine says modulator. A person adds a Move,
picks a preset, and drags one handle on the canvas; Advanced reveals source,
field, driver, and output when that vocabulary earns its place. Raw matrix
authoring stays inside Advanced; a node graph is deferred.

### Model

    driver -> source(cell, resolvedTime, inputs) -> envelope -> amount -> output

    type Move = {
      id: string;
      enabled: boolean;
      solo?: true;
      amount: number;                 // [0, 1] master, bindable later
      driver: "piece" | "beat" | "trigger" | "none";
      source: ModulationSource;       // ranked | sampled | controlled
      envelope?: RankEnvelope;        // static window and falloff over field value
      output: MoveOutput;             // discriminated by channel
    }

- `ModulationSource` is the partner's discriminated union. `signal x field`
  is only honest for separable sources; noise, media, and pointer are
  space-time sources and are typed as such.
- Fields return `{ value, gradient? }`. Offset may target a grid axis or the
  field gradient, which is how expansion from a sphere and flow around an
  origin are built without a global axis.
- Signals: sine, triangle, saw, pulse with duty, steps (N levels), quantize
  on any signal, polarity bipolar or positive. No easing on the oscillator:
  waveform plus quantize own shape.
- Every Move samples one immutable base context (document pose plus the
  resolved State morph). A later Move never sees an earlier Move's output.
- Channel algebra at one boundary, guarding non-finite values: offset adds;
  scale and opacity multiply and clamp; palette flip is parity; rotation folds
  in stack order as quarter-turn quaternions, so reorder is a real semantic
  operation and exists from slice 2; presence is never a Move target; grid
  gap and cell size run in a separate grid modifier phase after fields
  sample the base grid.
- Amplitude is lattice-relative (a fraction of the grid pitch), so a look
  survives a grid format change. This reverses the shipped world-unit choice;
  the reset makes it free. Stuart to confirm (question 1 below).
- `WaveTrack`, `set-piece-wave`, and their validation are deleted, not
  bridged. One coordinated reset of authored operation and structure record
  schemas.

### Slices

**1. Move library and kernel.** Ranked sources over the existing order fields
plus plane, sphere, and box; oscillator and step signals; envelope; offset
and scale outputs; presets Ripple, Lift, Steps, Jitter, Breathe; the Move card
with live field strip; Phase view tinting cells by field value; Advanced
disclosure with explicit origin; commit plays the piece. Acceptance: a strong
result in three actions or fewer, and each preset reads on line, plate, and
volume.

**2. Stack and canvas authorship.** N Moves with ids, mute, solo, and explicit
reorder; direct handles for origin, direction, radius, falloff; Motion Brush
for painted weights; part opacity and palette flip outputs; ordered rotation
prototyped and measured (Tumble) with resolved geometry inspected, not only
frame time; the composition boundary with tests per channel rule.

**3. Living sources.** Seeded four-dimensional coherent noise as signal and
field (Living Surface); the media luminance spike, with Display shipped only
on a non-blocking sampling path (low-resolution luminance atlas or GPU
sampling, never per-frame CPU readback); Orbit from the radial gradient.

**4. Live and recordable.** Pointer field with recorded gestures (Touch), beat
clock, trigger drivers with envelopes, audio and MIDI through the Performance
input seams, intensity bound to controls, fixed-step replay. Oscillator and
envelope kernels are shared with the Performance rig; clock and addressing
adapters stay separate, because the rig is structure-agnostic and the piece
score may address cube ids.

Edge weight is deferred behind a measured prototype in any slice; part
opacity ships first as the pulse.

### Acceptance bar for every slice

- Contract tests on the pure kernels, the document seam, and persistence.
- Browser proof of the pane and canvas handles; visual matrix on line,
  plate, and volume fixtures.
- Fixed-step replay produces identical resolved poses for the same document
  and recorded inputs.
- 12x12 plate and 20x20x20 volume profiled with no allocation in the per-cell
  inner loop.
- The authored schema cannot represent an unsupported source and channel
  combination.
- Delivery budget re-recorded.

### Decisions requested from Stuart

1. Amplitude lattice-relative rather than world units. Recommended yes.
2. Whole cycles stay the score contract until a one-shot piece exists.
   Recommended yes.
3. Part opacity before edge weight. Recommended yes.
4. Presets in code for slice 1, saved Move assets later. Recommended yes.
5. Slice 1 scope as written, or fold Phase view into slice 2 to ship sooner.
   Recommended as written: Phase view is what makes an invisible Move legible.
