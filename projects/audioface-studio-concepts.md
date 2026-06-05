---
title: Audioface Studio Layout Concepts
type: design
tags: [ux-design, information-architecture, audioface, studio, concepts]
summary: Four divergent layout concepts for the Audioface Studio redesign around a layered sound as the primary object.
status: active
source: ux-designer
confidence: medium
created: 2026-08-18
updated: 2026-08-18
---

# Audioface Studio Layout Concepts

Companion to `audioface-studio-ia-audit.md`. Four layout concepts for the inverted product: an unbounded studio for designing layered sounds first, interface semantics second.

Reference viewport for all proportions is 1440 x 900. Parameter pressure assumption is 100 to 170 controls per sound (roughly 30 per layer across source, filter, envelope, modulation, effects, and time, times 3 to 5 layers, plus identity and the 8 theme macros).

Mockups: `~/.mdx/projects/audioface-mockups/`, one 1536x1024 render per concept with its exact prompt beside it.

| Concept | Mockup |
|---|---|
| 1 Impact Bench | `concept-1-impact-bench.png` |
| 2 Patch Canvas | `concept-2-patch-canvas.png` |
| 3 Console | `concept-3-console.png` |
| 4 Feel First | `concept-4-feel-first.png` |

The renders illustrate structure and region proportion only. Colour, type, and surface treatment in them are not proposals.

## Shared invariants

True in all four. If a concept breaks one of these it is a defect in the concept, not a variation.

1. **One primary object.** The sound. A flow, a theme, and a token id are contexts attached to it.
2. **Theme is a lens, never a destructive edit.** The pipeline `definition -> theme resolve -> resolved layers -> engine` already supports this. The UI shows the unthemed definition and can overlay the themed result. This replaces the Raw / Themed debug pair.
3. **Analysis is always on screen.** Waveform, spectrum, or envelope, sized so a parameter change is visible without navigating.
4. **The layer is a first class object** with order, mute, solo, bypass, add, duplicate, delete, and keyboard reachability.
5. **Every parameter is addressable by name.** A command palette reaches any parameter in any concept. At 150 controls, search is not a convenience.
6. **Editing has memory.** Undo, per parameter revert, compare to saved, and two A/B snapshot slots.
7. **No raw ids or enums on screen.** Every identifier gets a designed label.
8. **Desktop and compact are two layouts, not one column count.** Each concept states what survives below 1024px.

---

## Concept 1: Impact Bench

*A layer stack over a millisecond time canvas.*

### Primary object and canvas

The sound as a stack of layers sharing one time ruler from 0 to about 600ms. The canvas is horizontal time by vertical layer, and every layer is a clip drawn in place: its waveform fills the clip, its amplitude envelope is drawn over it as a draggable curve, and its onset is its horizontal position. The premise is that interface sound is transient craft, and the thing that makes a sound work is the millisecond relationship between the click, the body, and the tail.

### Regions

```
+--------------------------------------------------------------------+
| transport  sound name | theme lens | velocity | audition     56px   |
+---------+----------------------------------------------+-----------+
| library |  SUM lane (summed waveform + playhead)  72px  | inspector |
| 240px   +----------------------------------------------+ 340px     |
|         |  ruler 0 . . 100 . . 200 . . 300 . . 400ms    |           |
| search  +----+-----------------------------------------+ Source    |
| sounds  |hdr | [clip: noise    ~~~~~ envelope curve  ]  | Filter    |
| by      |hdr | [clip: tone         ~~~~~~~~~~        ]  | Envelope  |
| category|hdr | [clip: fm      ~~~~~                  ]  | Modulation|
|         |hdr | [clip: tail            ~~~~~~~~~~~~~~ ]  | Effects   |
|         +----+-----------------------------------------+ Time      |
|         |  + add layer                                  |           |
+---------+----------------------------------------------+-----------+
| spectrum / spectrogram of last audition          200px             |
+--------------------------------------------------------------------+
```

Canvas is about 60% of width and 58% of height. Library rail collapses to 56px icons. Layer header is 160px: colour chip, name, type glyph, mute, solo, inline gain fader, level meter.

### Adding and editing a layer

Add layer opens a source picker (noise, tone, FM pair, sample-free impact model) and drops a clip at the playhead with sane defaults. Editing splits by tier:

- **On the clip, no panel**: drag body to move onset, drag right edge for duration, drag envelope handles for attack, decay, and curve, drag vertically for gain, alt-drag to duplicate.
- **In the inspector**: everything else for the selected layer, in six collapsible groups. Group open state is remembered per layer type, so a noise layer and a tone layer remember different shapes.
- **Per parameter**: alt-click any parameter opens a modulation popover (source, depth, range) so modulation never inflates the base rack.

Reorder by dragging a layer header. Solo is the workhorse: the sum lane keeps drawing the full sound so you always hear one layer in the context of the whole.

### Parameter disclosure

Three tiers as above: direct manipulation for the 6 parameters used constantly, grouped accordion for the ~30 per layer, popover for modulation state. Only one layer's rack is open at a time, which caps the visible rack at about 30 rows regardless of layer count. The command palette covers the rest.

### Audition and transport

Transport lives at the top-left of the canvas, not in a global header. Space triggers the sound and sweeps a playhead across the canvas so a designer can see which layer produced which transient. Clicking a layer header solo-auditions that layer. Velocity is a control next to the trigger because velocity changes the sound, and audition context (raw, themed, or inside a flow) is a segmented control beside it.

### Visual feedback

Waveform inside every clip, summed waveform in the sum lane, envelope curve drawn over the clip, per layer meters in headers, spectrum or spectrogram in the bottom strip. Every visual is in the time domain except the bottom strip, which is the deliberate counterweight.

### Optimizes for

Transient craft and layer timing, the actual daily work. Immediately legible: it reads as Photoshop layers crossed with a clip editor. Handles 3 to 8 layers gracefully. Lowest new-visual-language risk of the four.

### Sacrifices

Fixed per layer signal chain, so exotic routing and cross layer modulation are not expressible. Only one layer's parameters are visible at a time, so cross layer comparison ("what are the four cutoffs?") requires clicking. Filter and effects state is invisible on the canvas, so the canvas under-represents timbre. Comparing several sounds at once is not supported beyond the library rail.

### How semantics attach later

The canvas keeps its ruler, so the flow timeline docks below the analysis strip as a second, coarser time axis: selecting a step there swaps the canvas to that step's sound while the flow keeps playing. Theme becomes a lens toggle in the transport that redraws every clip with a ghost outline of the unthemed shape, which is a stronger answer than today's Raw / Themed buttons. Token identity, category, and action live in the library rail's detail panel. No structural rewrite: the flow strip and the theme lens are additive regions.

### Compact viewport

Canvas and sum lane survive full width. Inspector becomes a bottom sheet keyed to the selected layer. Library becomes a header select. Analysis strip collapses to a 64px waveform.

---

## Concept 2: Patch Canvas

*A modular signal chain on an open canvas.*

### Primary object and canvas

The sound as a signal graph. Sources, processors, modulators, and one output, connected by visible cables on a pannable canvas. A "layer" stops being a lane and becomes any source-to-output path; paths are visually grouped in tinted regions so the layer concept survives as a reading of the graph rather than a container.

### Regions

```
+--------------------------------------------------------------------+
| name | audition | theme lens | snapshot A/B                  52px   |
+--------+------------------------------------------------+----------+
| node   |          [OSC]---\                              | node     |
| palette|          [ENV]----[FILTER]---\                  | inspector|
| 220px  |                              [GAIN]---[OUT]     | 320px    |
|        |          [NOISE]--[HP]------/     |             |          |
| Sources|                                   |             | selected |
| Filters|          [LFO]~~~~~~~~~~~~~~~~~~~/              | node     |
| Envs   |                                                 | params   |
| Mod    |          o probe                                | 3-12 rows|
| FX     |                                                 |          |
+--------+------------------------------------------------+----------+
| scope dock: waveform | spectrum | envelope   (probe fed)    180px   |
+--------------------------------------------------------------------+
```

Canvas is about 66% of width and 74% of height. The scope dock collapses to 32px.

### Adding and editing a layer

Drag a source node from the palette onto the canvas and connect it toward the output; that is a new layer. Copy a whole path to duplicate a layer. Editing is node-local: select a node, its 3 to 12 parameters fill the inspector. Cross layer modulation is a cable, which is the thing no other concept can express: one envelope can drive four filters.

### Parameter disclosure

The graph is the disclosure. No parameter is more than one node click away and no rack ever exceeds a single screen, because complexity lives in topology rather than in list length. Two extra mechanisms: node collapse folds a group of nodes into one macro node with a handful of exposed knobs, and that same mechanism later becomes how theme macros and shipped presets are built. Probes are the inspection primitive: drop one on any cable and the scope shows the signal at that point.

### Audition and transport

There is no playhead, so transport is minimal: a trigger, a velocity control, and a repeat toggle. Space triggers the patch. Each node carries a monitor tap so you can audition the signal at any point in the chain, which is the concept's answer to "what is this node doing".

### Visual feedback

Animated signal presence on cables, per node micro-displays (an envelope node draws its curve, a filter node draws its response), and the probe-fed scope dock. Time relationships are only visible if a delay node states them numerically, which is this concept's blind spot.

### Optimizes for

Unbounded synthesis. It is the only concept where the parameter count can grow indefinitely without the layout degrading, because new capability arrives as new node types. It teaches the signal path, matches the resolver's existing DAG thinking, and gives modulation a natural home.

### Sacrifices

Millisecond timing legibility, the thing interface sound depends on most. Speed for the common edit: changing one gain means finding a node. Spatial memory cost grows with patch size, and patch spaghetti is a real failure mode. Highest engineering cost, the weakest narrow-viewport story, and the strongest pull toward general purpose synth language, which is exactly what `ARCHITECTURE.md` warns against for Score Mode.

### How semantics attach later

Best theme story of the four: the eight theme macros become a Theme Rack docked left of the canvas whose dials are literal cables into parameters, so the macro to parameter mapping is visible and editable rather than hidden in resolver code. A flow becomes a Sequencer node driving trigger inputs. A token is a saved patch with a semantic id. The existing `SequenceGraph` stub becomes a real feature instead of an assertion.

### Compact viewport

Poor. Realistically a read-only patch viewer plus the macro rack; authoring stays desktop.

---

## Concept 3: Console

*A dense fixed-architecture rack under a large scope.*

### Primary object and canvas

The sound as a set of channel strips. Every layer has the same modules in the same order; only the values differ. Because the architecture is fixed, everything can be on screen at once, and the design loop becomes change a number, watch the scope.

### Regions

```
+--------------------------------------------------------------------+
| button.press x | toast.arrive x | confirm x        + tabs     48px  |
+--------------------------------------------------------------------+
|                                                                     |
|   SCOPE   waveform + envelope overlay + ghost trace of previous     |
|           tabs: wave | spectrum | spectrogram | transient   340px   |
|                                            [trigger] [vel] [auto]   |
+--------------------------------------------+-----------+-----------+
| L1 NOISE      | L2 TONE       | L3 FM      | L4 TAIL   | MASTER    |
| Source  v     | Source  v     | Source  v  | ...       | 200px     |
|  colour  ---- |  wave    ---- |  carrier   |           | out gain  |
|  density ---- |  freq    ---- |  mod       |           | limiter   |
| Filter  v     | Filter  v     | index      |           | theme     |
|  cutoff  ---- |  cutoff  ---- | Filter  v  |           |  8 macros |
|  res     ---- |  res     ---- | ...        |           |  material |
| Env     v     | Env     v     |            |           |           |
|  a d s r ---- |  a d s r ---- |            |           | raw/theme |
| Mod  > FX  >  | Mod  > FX  >  |            |           |  A/B      |
| 280px         | 280px         | 280px      | 280px     |           |
+---------------+---------------+------------+-----------+-----------+
| cmd-K parameter search | filter: modified only | 32px              |
+--------------------------------------------------------------------+
```

Scope is 38% of height and full width. Rack is 52% of height, strips scroll horizontally, master strip is pinned right. Rack rows are 24px with a 12px label, numeric field, thin slider, and a modulation dot.

### Adding and editing a layer

Add layer appends a strip and scrolls to it. Reorder by dragging a strip header. Mute, solo, and bypass are in the strip header. Editing is direct: click a numeric field and type, or drag the slider. Nothing is behind navigation. Modules collapse per strip, and collapse state can be applied across all strips at once.

### Parameter disclosure

Density first, hiding last. Three assists rather than a hierarchy:

- **Module collapse**, per strip or across all strips.
- **Focus rows**: show one module group across every layer, turning the rack into a comparison table ("all four cutoffs, side by side"). This is the move no other concept can make.
- **Modified only**: filter the rack to parameters that differ from the canonical default, which usually collapses 150 rows to 12.

Plus cmd-K to jump to any parameter by name.

### Audition and transport

Pinned bottom-right of the scope. The defining interaction is auto-audition: retrigger on every parameter change, so a drag becomes a continuous listening loop with no click. Velocity sits next to the trigger. Recently opened sounds live as editor-style tabs at the top, which makes A/B across sounds a keystroke.

### Visual feedback

The scope dominates and every change writes to it: the previous value leaves a ghost trace for two seconds so a parameter's effect is visible rather than remembered. Per strip meters, per parameter modulation dots that fill to show live modulated value.

### Optimizes for

Expert speed and precision. It is the only concept that never hides a parameter, the only one that compares layers on a shared axis, and the only one where an edit is a keystroke rather than a gesture. Scales to 200 parameters without a layout change.

### Sacrifices

Approachability. It reads as a mixing desk, which is wrong for the product designer persona Audioface is otherwise aimed at. Requires 1280px or more; compact becomes a separate reduced app. The fixed architecture makes exotic routing impossible by construction, which is a feature for consistency and a wall for exploration. Time relationships between layers are numeric rather than visual.

### How semantics attach later

Semantic identity lives in the tab bar and a properties popover. Flows attach as a playlist beside the transport, so a sound is auditioned inside Command Flow without leaving the rack. Theme is already drawn as the master strip: the eight macros ride there, and the scope shows raw and themed as two traces. Because the architecture is fixed, theme mapping is expressible as per parameter depths, which is the cleanest implementation path of the four.

### Compact viewport

Scope plus one strip at a time with a strip pager. Honest but weak; treat mobile as review and audition, not authoring.

---

## Concept 4: Feel First

*A semantic macro surface with recursive depth.*

### Primary object and canvas

The sound as a feel: material plus eight macros, rendered as one recognisable shape. The full parameter tree exists but is folded underneath the macro that drives it. The designer works at the top of the abstraction and drills only where the result is wrong. The neighbouring sounds in the same set are always visible, because Audioface's real product value is consistency across a token set, not one perfect sound.

### Regions

```
+--------------------------------------------------------------------+
| set name | audition | compare | export                       52px  |
+----------+---------------------------------------+----------------+
| TOKEN    |   material: soft ceramic rubber ...   | DEPTH COLUMN   |
| WALL     |                                       | 360px          |
| 280px    |        density        contrast        |                |
|          |            \           /              | > Layers (4)   |
| [shape]  |             +---------+               |                |
| [shape]  |   warmth ---|  SOUND  |--- mechanical | selected macro |
| [shape]  |             |  SHAPE  |               |  drives:       |
| [shape]  |             +---------+               |  cutoff  ###   |
| [shape]  |            /           \              |  res     ##    |
| [shape]  |      politeness    variation          |  decay   ####  |
|          |                                       |                |
| sibling  |            volume                     | [open full     |
| sounds   |                                       |  rack]         |
+----------+---------------------------------------+----------------+
| audition strip: flow context | compact spectrum + envelope  120px  |
+--------------------------------------------------------------------+
```

Feel surface is about 46% of width. Token wall is a grid of miniature shape renderings of every sibling sound in the set.

### Adding and editing a layer

Layers are behind the depth column's Layers row, not on the main canvas, which is the concept's central bet: most edits should not require thinking in layers. Opening Layers gives a compact stack (add, duplicate, mute, solo, reorder) and selecting one populates the depth column with its groups. The escape hatch is explicit: **open full rack** expands the depth column to a Console-style rack for the current layer, so depth is never unreachable, only unimposed.

### Parameter disclosure

Recursive drill through the macro graph, the only concept whose disclosure path is semantic rather than structural:

1. **Feel**: material and eight macros.
2. **What it drives**: click a macro and the depth column lists every parameter it modulates, with current value and modulated range.
3. **The parameter**: click one and get its full editor, with the macro's contribution drawn as a shaded band around the base value, so the designer sees why it moved.

Two consequences. The path from "this feels wrong" to "this parameter is why" is three clicks and no searching. And every new parameter must be mapped to a macro or it becomes unreachable except through the full rack.

### Audition and transport

Continuous and ambient. Every macro gesture retriggers on release, the token wall auditions on hover, and the bottom strip carries the flow context so a sound is heard in its sequence without a mode change. No playhead, no timeline.

### Visual feedback

The sound shape is the primary visual: one rendering combining amplitude silhouette, spectral colour, and decay length, drawn identically at large size in the centre and at thumbnail size across the wall. Identity at a glance and comparability across a set. Compact spectrum and envelope in the bottom strip carry the analytical load.

### Optimizes for

The Audioface promise and the product designer persona. Set level consistency, which no other concept surfaces at all. Shortest diagnostic path from perception to cause. Strongest onboarding story and the best fit for the existing eight macro vocabulary.

### Sacrifices

Low level editing speed; a synthesis designer will resent the drill and live in the escape hatch. Requires the macro to parameter mapping to be authored, documented, and maintained for every parameter added, a permanent cost, and a thin mapping makes the drill lead nowhere. The sound shape is a novel visual language that must be invented and validated; it is the highest design risk here. Time relationships between layers are invisible.

### How semantics attach later

Inverted risk: this concept *is* the semantics layer, so the open question is whether it can host deep synthesis at all, which is what the full rack escape hatch answers. Flows become a fourth level of the same drill, with set, sound, macro, and parameter above them, and the bottom strip already holds the flow context.

### Compact viewport

Best of the four. The feel surface and audition strip are already touch scale; the token wall becomes a horizontal filmstrip and the depth column a sheet.

---

## Comparison

| | Impact Bench | Patch Canvas | Console | Feel First |
|---|---|---|---|---|
| Primary canvas | layer clips on ms time | node graph | scope over rack | macro surface |
| Disclosure | clip, accordion, popover | topology and node collapse | density, collapse, focus rows | recursive semantic drill |
| Scales to 170 params | good | excellent | excellent | good via escape hatch |
| Layer timing legible | excellent | poor | numeric only | none |
| Cross layer comparison | poor | poor | excellent | none |
| Free routing | none | excellent | none | none |
| Novice legibility | good | poor | poor | excellent |
| Set consistency | weak | none | tabs only | excellent |
| Visual language risk | low | medium | low | high |
| Build cost | medium | high | medium | medium-high |
| Compact viewport | fair | poor | poor | good |

## How to decide

The four are not ranked; they answer different questions. The discriminating questions, in the order they matter:

1. **Who is the daily user?** A sound designer who thinks in transients points at Impact Bench or Console. A product designer who thinks in feel points at Feel First.
2. **Is free modulation routing a product requirement or a synthesis reflex?** If a fixed per layer chain covers the token catalogue, Patch Canvas is expensive expressiveness. If cross layer modulation is how the material model gets its life, nothing else will do.
3. **Does the product need set consistency to be visible while editing?** Only Feel First shows it, and it is arguably Audioface's most defensible differentiator.
4. **What is the smallest thing that beats the current Studio?** Any of the four beats it, because all four have a primary object, a primary surface, and an analysis view.

Designer's read, offered as opinion rather than finding: Impact Bench is the strongest base because its canvas teaches the domain and its risk is lowest, Console's focus rows and auto-audition are the two mechanics most worth stealing into it, Feel First is the right shell to wrap around it once the depth exists, and Patch Canvas is the advanced mode to earn later, in the same spirit `ARCHITECTURE.md` reserves for Score Mode.

## Open questions

1. Does a sound need free modulation routing, or is a fixed per layer chain sufficient for the token catalogue?
2. Is the macro to parameter mapping authored by hand per parameter, or derived from parameter metadata? Feel First's cost hinges entirely on this.
3. Is mobile authoring a requirement, or is compact a review and audition surface?
4. Does the sound shape visual survive a legibility test at thumbnail size across a 30 token set?
5. Do canonical Audioface tokens remain locked once the parameter surface is this deep, or does locked become a fork-on-edit affordance?
