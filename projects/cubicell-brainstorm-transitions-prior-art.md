# Prior art: enter / update / exit when interpolating two authored states

**Task:** survey how existing systems name and control the three populations that appear when you interpolate between two discrete authored states: subjects that exist in both (matched), only in the second (entering), only in the first (leaving).

**Constraint honored:** cubicell source was not read. This is vocabulary and UX from external systems only.

**Abstract problem restated.** A tool has state A and state B. Each state is a set of subjects. Matched subjects have a well-defined interpolant (position, scale, color, …). Entering and leaving subjects have no interpolant unless the author supplies one. Authors of large sets cannot hand-author per-subject behaviour; the system must expose population-level controls and sane defaults.

---

## 1. Per-system survey

### 1.1 D3 (data join / general update pattern)

| Question | Answer |
|----------|--------|
| **Names** | **enter**, **update**, **exit** (plus the merged enter+update after `selection.join`). Classic Mike Bostock terms; still the industry root vocabulary for this problem. |
| **Matching** | Optional **key function** on `selection.data(data, key)`. Default is **index join** (i-th datum binds to i-th element). Key function returns a string identity (e.g. `d => d.id`). Mis-match: wrong key → element treated as exit + new enter (destroy/recreate); index join on reordered data → subjects morph into each other’s identity. |
| **Author vocabulary** | Explicit three-way: `selection.join(enterFn, updateFn, exitFn)` or the older enter/exit/merge pattern. Enter: typically `append` + initial attrs + transition to final. Exit: typically transition then `remove()`. Update: transition attrs. Controls are **code callbacks per population**, not per subject: as few as three functions for hundreds of nodes. |
| **Friendly / hostile** | **Friendly once you learn the model; hostile to newcomers.** Failure mode users complain about: silent **index joining** when they forget a key, so list reorder “animates” as content swap rather than spatial shuffle. Second complaint: exit without `remove()` leaves ghost DOM; enter without merge leaves update attrs unapplied. |

**Population-level expression:** the whole point of the join. One enter policy, one exit policy, one update policy.

**Default:** `selection.join()` with no args: enter appends, exit removes immediately, update is identity. Instant pop-in/pop-out. Authors almost always override enter/exit with a fade or size transition.

---

### 1.2 React Transition Group (RTG)

| Question | Answer |
|----------|--------|
| **Names** | Lifecycle phases: **appear**, **enter**, **exit** (and CSS class suffixes: `-enter`, `-enter-active`, `-enter-done`, `-exit`, `-exit-active`, `-exit-done`). Matched/staying subjects are just “present children”; there is no first-class **update** name for property interpolation. |
| **Matching** | React **`key`** on list children inside `TransitionGroup`. Same key across renders = same component instance (can enter/exit). Index keys or unstable keys → remount → spurious exit+enter. |
| **Author vocabulary** | Per component type (or shared via `classNames` / `timeout`): appear/enter/exit durations, CSS class names, optional `addEndListener`. `SwitchTransition` for mutually exclusive children (`mode="out-in"` \| `"in-out"`). Controls are **class-driven stage hooks**, not spatial morphs. Roughly 2–4 knobs (timeout enter/exit, classNames, mode). |
| **Friendly / hostile** | **Hostile for layout morphs; adequate for fade/slide mount.** Classic failure: exit animation never runs because the component unmounted without `TransitionGroup` keeping it mounted for `timeout`. Second: timeout/CSS duration mismatch leaves stuck classes. RTG does **not** interpolate layout between two positions of a surviving key; that is out of scope. |

**Population-level:** yes via shared `classNames` and `timeout` on the group’s children of one type. Per-instance override is possible but uncommon.

**Default:** no animation unless you wire CSS/timeout. Zero is the default; appearance is abrupt.

---

### 1.3 Framer Motion / Motion (`AnimatePresence` + layout)

| Question | Answer |
|----------|--------|
| **Names** | **initial** / **animate** / **exit** for presence; **layout** / **layoutId** for shared-element / FLIP-style layout. `AnimatePresence` **mode**: `sync` (default), `wait`, `popLayout`. Surviving matched items are layout-animated; no single word “update” but **layout** is the matched path. |
| **Matching** | React **`key`** for presence identity. **`layoutId`** for shared element morph across tree positions (same id → crossfade/morph between instances). Mis-match: missing `key` → remount thrash; colliding `layoutId` → wrong pairing; exit without `AnimatePresence` → no exit animation (instant unmount). |
| **Author vocabulary** | Population-friendly: set `initial`, `animate`, `exit` once on the list item component; set `layout` once; wrap list in `AnimatePresence`. Extra knobs: `mode`, `transition` (spring/duration), `onExitComplete`. Roughly **one presence triple + one layout flag + optional mode**. |
| **Friendly / hostile** | **Friendly for lists when keys and AnimatePresence are correct; sharp edges elsewhere.** Failure modes: exit never fires (forgot wrapper); jump during exit until `mode="popLayout"` (exit still occupies layout); shared layout “jank” when parent isn’t positioned; custom components must `forwardRef` under `popLayout`. |

**Population-level:** declarative props on the component definition apply to every instance. Authors almost never set per-item enter/exit differently.

**Default worth stealing:** `mode="sync"` (enter and exit concurrent) + fade/scale exit recipes in docs. For lists, the **winning default pattern** is `layout` + `exit={{ opacity: 0 }}` + `mode="popLayout"` so leavers fade while survivors FLIP into new slots.

---

### 1.4 FLIP (Paul Lewis: First, Last, Invert, Play)

| Question | Answer |
|----------|--------|
| **Names** | Not a presence model. Stages: **First**, **Last**, **Invert**, **Play**. Applies only to **elements that exist before and after** the change. Enter/leave are out of band. |
| **Matching** | Caller must supply identity (DOM node map by id). No built-in join. |
| **Author vocabulary** | Technique, not product. You implement: snapshot rects → commit new layout → invert with transform → transition transform to identity. Enter/leave still need separate opacity/size work (often “scale from 0” / “scale to 0” or fade). |
| **Friendly / hostile** | **Friendly performance story; incomplete problem coverage.** Failure modes: parent scale/border-radius skew; text reflow mid-FLIP; enter/leave not handled so lists still “pop” unless you add presence. |

**Implication for the abstract problem:** FLIP is the **matched-population engine**. It does not solve enter/leave. Systems that feel good (Motion layout, FLIP lists) always pair FLIP with a separate presence policy.

---

### 1.5 Figma Smart Animate

| Question | Answer |
|----------|--------|
| **Names** | Informal: **matching layers** vs non-matching. Non-matching destination layers **dissolve into view**; non-matching origin layers dissolve out (or follow the main transition when using “Smart animate matching layers” with Push/Slide). No public enter/update/exit branding, but behaviour is join-like. |
| **Matching** | **Exact layer name + hierarchy position** (parent chain). Duplicate frames preserve names. Mis-match is **silent**: typo, rename, or hierarchy drift → dissolve instead of morph. Same name in different parents may fail. Unsupported properties (some effects, shape type changes) fall back to dissolve. |
| **Author vocabulary** | Extremely small: choose **Smart animate** (or checkbox **Smart animate matching layers** on another transition), set **duration** and **easing**. Appear/disappear: set opacity 0% on one side (docs recommend opacity, not visibility toggle). No per-layer enter recipe UI; population behaviour is global to the transition. ~**2–3 knobs**. |
| **Friendly / hostile** | **Magic when names align; “forever hell” when they don’t.** Dominant complaint: silent dissolve, no diagnostics; hierarchy sensitivity; identical names for list rows cause content morph instead of enter/exit (docs themselves show grouping/renaming as the fix). |

**Default:** matched layers interpolate supported props (position, size, opacity, rotation, fill); **new layers dissolve in**. That dissolve default is the 80% author never overrides.

---

### 1.6 Keynote Magic Move

| Question | Answer |
|----------|--------|
| **Names** | **Magic Move** transition. Objects “in common” move; others effectively fade. No formal enter/exit API. |
| **Matching** | Heuristic **identity / sameness** of objects across consecutive slides (duplicate-slide workflow). Text must be present on both slides to move (builds that bring text in later break matching). Similar shapes can mis-pair; advanced users force match by grouping unique invisible geometry with each object. |
| **Author vocabulary** | One transition type + duration/acceleration. No population recipes. ~**1–2 knobs**. |
| **Friendly / hostile** | **Friendly for simple decks; brittle with many similar objects.** Failure mode: arrows/shapes swap partners; groups all named “group” reduce control; authors resort to hacky unique-shape companions to force pairing. |

---

### 1.7 PowerPoint Morph

| Question | Answer |
|----------|--------|
| **Names** | **Morph** transition. Matched objects morph; unmatched appear/disappear as part of the morph transition. |
| **Matching** | Default: **visual similarity / type** heuristics. Explicit override: Selection Pane names starting with **`!!`** force 1:1 match of same `!!Name` across slides. Rules: `!!` only matches `!!`; expects unique name per slide. Mis-match without `!!` → wrong partner or dissolve-like behaviour. |
| **Author vocabulary** | Apply Morph on destination slide; optional `!!` naming; duration. ~**1–2 knobs** plus optional identity annotation. |
| **Friendly / hostile** | **Very friendly when you duplicate-then-edit.** Hostile when many similar shapes need different destinations without `!!` (common “Morph troubles” thread pattern). `!!` is the escape hatch designers learn late. |

**Default:** one transition type does join + interpolate; authors rarely configure enter/leave separately. Unmatched objects fade as part of Morph.

---

### 1.8 After Effects

| Question | Answer |
|----------|--------|
| **Names** | Timeline model: **layers**, **keyframes**, **in/out points**, optional **opacity** / **scale** for birth/death. Shape **path morph** is point-to-point on a single path, not a set join. No enter/update/exit data model. |
| **Matching** | Manual: same layer continues; or two shape paths with compatible vertex counts for morph. Mis-match: path morph flips/winds; new layer is a hard cut unless keyframed. |
| **Author vocabulary** | Unlimited keyframe control; **hostile at scale** for hundreds of subjects. Population-level only via expressions, essential graphics, or scripts/plugins. Default for “new layer” is **pop on** at in-point. |
| **Friendly / hostile** | **Hostile for the abstract problem.** Failure mode: morphing icons with unequal points; per-layer keyframing doesn’t scale; “just keyframe opacity” is the ad-hoc enter/exit. |

AE is the proof that **manual timelines do not solve population enter/exit** without tooling on top.

---

### 1.9 Blender

| Question | Answer |
|----------|--------|
| **Names** | **Keyframe** visibility (`hide_viewport` / `hide_render`), **opacity** in materials, **shape keys** (basis vs relative keys) for mesh morphs. No set-join vocabulary. |
| **Matching** | Same object datablock across frames. Shape keys morph geometry of **one** mesh; they do not join two object sets. New objects appear when visibility/render toggles or scale/opacity keyframes allow. |
| **Author vocabulary** | Per-object keyframes or drivers. Collections help organization, not transition policy. Population behaviour requires scripting (Python) or Geometry Nodes patterns. |
| **Friendly / hostile** | **Hostile for set interpolation.** Shape keys solve “one mesh, many shapes,” not “N cubes, some born, some die.” Users animate appear/disappear with scale/opacity hacks. |

---

### 1.10 Rive

| Question | Answer |
|----------|--------|
| **Names** | **State machine**, **animation states**, **transitions**, **inputs** (bool/number/trigger), **blend**. Subjects are authored artboard nodes, not data-joined instances. |
| **Matching** | Pre-authored identity: the same node in the artboard across animations. No runtime join of arbitrary data subjects. |
| **Author vocabulary** | Design-time: timelines + state graph conditions. Runtime: flip inputs. Enter/leave of dynamic list items is **not** the product’s primary model (lists are usually host-app DOM/Flutter/etc.). |
| **Friendly / hostile** | **Friendly for fixed interactive graphics; wrong tool for data-driven set diffs.** Failure mode: trying to drive hundreds of data-bound cubes purely from Rive without host-side join logic. |

---

### 1.11 CSS View Transitions API

| Question | Answer |
|----------|--------|
| **Names** | **old** / **new** snapshots; **`::view-transition-group(name)`**, **`::view-transition-old(name)`**, **`::view-transition-new(name)`**. Enter/exit via **`:only-child`** on old or new (only old = leaving; only new = entering). Matched name → group with both old and new (morph/crossfade pair). Root group is default page crossfade. |
| **Matching** | Explicit **`view-transition-name`** (unique per document). Same name in old and new DOM → paired morph. Mismatch / missing name → element participates only in root crossfade or not at all. Duplicate names invalid. `match-element` (newer) auto-generates stable ids for list rows. |
| **Author vocabulary** | CSS animations on the pseudo-elements; optional JS `document.startViewTransition`. Population-level: one rule for `::view-transition-new(*):only-child` enter, one for old exit, one for groups. ~**3 CSS recipes** cover the three populations. |
| **Friendly / hostile** | **Friendly defaults; sharp name uniqueness rules.** Failure modes: two elements with same name; forgetting name so shared element doesn’t morph; enter/exit customization requires knowing `:only-child` trick. |

**Default:** **cross-fade**. Named elements get a default morph (position/size of the group) plus crossfade of old/new content. Authors often never customize enter/exit beyond the default fade.

---

### 1.12 Adjacent: list reorder models (summary)

| System | Matched | Enter | Leave | Match key |
|--------|---------|-------|-------|-----------|
| Auto-Animate / FLIP lists | FLIP transform | fade/scale-in | fade/scale-out | id |
| React `key` + Motion | layout prop | initial→animate | exit | key / layoutId |
| CSS VT list rows | named groups | only-child new | only-child old | view-transition-name |

---

## 2. Synthesis

### 2.1 Smallest control vocabulary that covers real intent (ruthless)

**80% case:**  
“Things that stay should move smoothly into their new pose. Things that appear should fade (or scale) in. Things that leave should fade (or scale) out. One duration/easing for the whole transition.”

**One knob that buys the 80%:**  
A single **population presence policy** applied to all unmatched subjects:

> **matched → interpolate authored properties; enter → fade in; leave → fade out**

Optional second knob (only when lists reflow): **layout/FLIP for survivors while leavers are removed from flow** (Motion `popLayout`, FLIP lists).

Everything else (directional wipe, particle dissolve, staggered delay, spring vs ease, per-subject override) is the long tail.

Minimal author surface:

1. **Identity** (how subjects match): required, once, by id.  
2. **Presence default** for enter/leave: fade (or scale+fade).  
3. **Timing**: duration + easing (one pair for all three populations is enough for 80%).  
4. Optional: **stagger** as a single population parameter, not per subject.

Do **not** start with per-subject enter recipes. Do **not** require timeline keyframes for birth/death.

### 2.2 Defaults so good authors never touch the control

| System | Default that carries most work |
|--------|--------------------------------|
| **Figma Smart Animate** | New/removed layers **dissolve**; matched layers auto-interpolate supported props. Authors only rename layers carefully. |
| **CSS View Transitions** | **Cross-fade** root; named pairs morph with default animations. Enter/exit customization is opt-in via `:only-child`. |
| **PowerPoint Morph / Keynote Magic Move** | One transition type: common objects morph, others fade. Zero enter/exit UI. |
| **Motion `AnimatePresence`** | Docs push `opacity: 0` enter/exit; `layout` handles survivors. |
| **D3 `join()`** | Instant append/remove (works for charts until you care about polish); community default overlay is short opacity transition. |

**Best single default across the survey:**  
**Dissolve / cross-fade for enter and leave**, with automatic property interpolation only for matched subjects.  
**Primary source systems:** Figma Smart Animate (documented dissolve for new layers) and CSS View Transitions (default cross-fade). Slide tools (Morph / Magic Move) independently converged on the same default.

Instant remove (raw D3 join, React unmount without presence) is a **bad** default for authored visual states; it is a good default for pure data DOM.

### 2.3 Express once for a whole population

| System | How |
|--------|-----|
| **D3** | `join(enter, update, exit)` — three functions, all nodes of that selection. |
| **Motion** | `initial` / `animate` / `exit` / `layout` on the item component; `AnimatePresence` on the list. |
| **RTG** | Shared `classNames` + `timeout` on every `CSSTransition` child of a type. |
| **Figma / Morph / Magic Move** | One transition setting on the frame/slide pair; no per-layer enter UI. |
| **CSS VT** | Global CSS rules targeting `::view-transition-old/new` and groups. |
| **AE / Blender / Rive** | Weak: per-layer or pre-authored graph; population only via script or host app. |

Pattern: **identity on the subject, policy on the population, timing on the transition.**

### 2.4 Three traps designers (and product designers of tools) do not anticipate

1. **Identity is the product.**  
   Index join, visual similarity, or “same layer name” without hierarchy discipline causes **wrong morphs** (content A animates into B’s pose). Users describe this as “broken animation,” not “bad matching.” Escape hatches that work: explicit ids (`key`, `!!name`, `view-transition-name`, D3 key function). Heuristic matching without a force-id will eventually betray large sets of similar cubes.

2. **Silent fallthrough.**  
   Figma dissolves on mis-match; Morph/Magic Move fade; CSS VT drops to root crossfade. There is **no error**. Authors spend hours “fixing Smart Animate” when the real bug is a renamed layer. A tool for hundreds of subjects needs **match diagnostics** (count enter/update/exit, highlight orphans), not only prettier defaults.

3. **Exit still occupies layout (or vanishes without animation).**  
   Two opposite failures:  
   - Unmount immediately → no leave animation (React without `AnimatePresence`).  
   - Leave animates but still takes space → survivors jump late (Motion without `popLayout` / absolute exit).  
   Authors do not expect that “fade out” and “reflow survivors” are **coupled policies**. The good list pattern is: pop leaver out of flow **and** fade it, while survivors FLIP.

**Bonus trap (fourth, still common):** hierarchy/parent changes break name+path matching (Figma) even when leaf names match. Data models that match by **stable subject id independent of parent** age better than name-in-tree.

---

## 3. Term-of-art cheat sheet

| Population | D3 | RTG | Motion | CSS VT | Figma | Morph/Magic Move |
|------------|----|-----|--------|--------|-------|------------------|
| Matched | **update** | (present / no name) | **layout** / **animate** | old+new **group** | **matching layers** | common / morphing objects |
| Entering | **enter** | **enter** / **appear** | **initial → animate** | **::view-transition-new:only-child** | new layer (dissolve in) | objects only on destination |
| Leaving | **exit** | **exit** | **exit** | **::view-transition-old:only-child** | removed layer (dissolve out) | objects only on origin |

**Match mechanisms ranked by reliability for large similar sets:**

1. Explicit stable id (D3 key, React key, `!!` name, `view-transition-name`, `layoutId`)  
2. Name + hierarchy (Figma)  
3. Visual similarity (default Morph / Magic Move)  
4. Index (D3 default, React index keys) — **avoid**

---

## 4. Recommendation distilled for a lattice/subject tool

Steal this stack, not any one product wholesale:

1. **Join model:** D3 names (**enter / update / exit**) for the engine and docs.  
2. **Default policy:** Figma / CSS VT — **fade unmatched; interpolate matched**.  
3. **Matched motion:** FLIP / layout for pose changes when topology of survivors shifts.  
4. **Author surface:** population-level once (one enter recipe, one exit recipe, one timing), identity by **subject id**, never by index or visual hash alone.  
5. **Honesty UI:** show enter/update/exit counts; never silent-only dissolve on mis-match without a way to inspect pairing.

**Single best default found:** unmatched subjects **dissolve (opacity cross-fade)** while matched subjects interpolate properties — from **Figma Smart Animate** (documented dissolve for non-matching layers) with independent confirmation from **CSS View Transitions** default cross-fade and slide-tool Morph/Magic Move behaviour.
