# Cubicell: keyboard-first grid selection navigation (SELECT mode)

v0.3, 2026-07-11. Fable (8:4.1) holds the pen. Folded: Grok (build
pragmatics), Opus (state architecture), Codex (prior-art rigor), and
Stuart's rulings on persistence, the depth key, and the ship-bar
hatch. All 10 open questions resolved below. Depth key and ship-bar
hatch finalized per Stuart. This is a
**rung-0 direct-manipulation** feature (reaching and moving the
selection cursor on the canvas), distinct from the selection *query
authoring* surface designed in
[cubicell-select-ux-proposal.md](cubicell-select-ux-proposal.md). The
two compose but do not overlap: this spec is how you point at a cube you
cannot see; that proposal is how you generalize from one you can.

The boundary, precisely: numpad nav reaches the exemplar (the pick);
the query-verb surface expands it (the bloom). Shift+numpad is by-hand
growth; verbs are by-rule growth.

## The problem

Three concrete gaps, surfaced live on a 3x3x3.

1. **The buried cube is unreachable by pointer.** The center cube of a
   3x3x3 is at grid coordinate (1,1,1). It has zero faces visible from
   any orbit angle (and after the face-culling work it draws zero
   faces, period), so a raycast click can never hit it. Mainstream
   tools reach occluded geometry many ways: outliners, select-through
   filters, isolate modes, section planes, coordinate entry. Cubicell
   picks a grid-native cursor because its integer lattice makes that
   unusually direct; a mesh modeler has no such lattice to lean on.

2. **No keyboard drive for the selection.** The pointer is the only way
   to move what is selected. There is no "nudge the selection one cube
   over" and no axis-locked navigation.

3. **The selection is nearly invisible on wireframe cubes.** With a
   cube rendered edges-only, the current selection treatment (grey
   `#9a9a9a` chrome) does not read. The selected cube must carry a real
   highlight color, not a subtle edge state.

## The model, in one line

**A viewport `SELECT` mode that pins the camera to an axis, turns the
grid into a 2D navigable plane driven by the numpad, re-pins between the
six orthographic axes on demand, and steps depth along the view axis;
the selected cube always carries a saturated highlight color.**

Prior-art honesty (Codex): two-view orthographic positioning is
established practice (Blender documents placing the 3D Cursor by two
axis views). A keyboard *selection cursor* navigating a lattice this
way is Cubicell-specific. The mental model is validated; the mechanism
is ours.

### 1. ORBIT | SELECT viewport nav mode

A two-state tab in the viewport chrome (mock: image #4, alongside the
existing tab). This is a **new mode dimension**, and its home is ruled:

- **`editor.navMode: 'orbit' | 'select'`**, a new editor-session field.
  Session-only, always boots ORBIT on cold start (Stuart's ruling). Not
  a preference, not persisted. The editor session lives in neither
  persisted state nor `DocumentHistory`, so undo-exclusion is free by
  construction; nothing to wire.
- Rejected: folding into `viewportMode` (that is a persisted preference
  governing focus-framing scope, a different concern) and deriving from
  camera state (fragile; cannot represent SELECT during the entry
  morph).

- **ORBIT** (default): today's free camera. Unchanged.
- **SELECT**: on entry, the camera snaps to the nearest axis-aligned
  orthographic pose. The grid flattens to a clean 2D face. Keyboard
  drives the selection cursor (below).

**Fluid handoff (no manual wrestling):**
- A mouse-orbit gesture while in SELECT auto-returns to ORBIT. You
  never toggle out to look around; grabbing the view *is* the toggle.
  Implementation: a hook at the gesture boundary in
  `cameraGestureRuntime.ts` (`core.gesture.begin`), not just the tab
  click.
- Entry and every re-pin click snap to the **nearest** axis (ruling,
  Q2): least camera travel, and the camera is wherever the user just
  left it. Last-pinned would teleport across the scene after any orbit.
- Entry **forces orthographic projection** (ruling, Q3; Codex confirms
  reference-faithful) and morphs via the existing projection machinery,
  `recordHistory: false`. The pre-entry projection is captured in
  transient session state (`editor.navPriorProjection`) and restored on
  exit. Edge case: if the user presses P while in SELECT, drop the
  capture and honor their explicit choice on exit.

**Camera mechanism (Grok correction):** `orbitDetent.ts` is a
*relative* 45-degree step animator, not an absolute world-axis snap; it
stays ORBIT-only. SELECT entry and the six axis pins ride the existing
absolute pose vocabulary: `FocusViewOrientation
{ kind: 'direction', direction, up }` (`src/pose/focusView.ts`)
dispatched as focus/reset view commands on the view lane. The six pins
are new registered affordances (none exist today), so palette and
keymap rows come free.

### 2. Numpad as the 2D map

In SELECT, the numpad is the plane. This **rebinds** the numpad, which
today drives orbit (`keymap.ts`: `numpad1..9 -> viewOrbit*`).

**Deliberate remap (Codex):** Blender's numpad is views (1/3/7 front,
right, top; Ctrl variants for opposites; 2/4/6/8 orbit; 5 projection).
We knowingly trade that away: in SELECT the physical numpad is a
spatial map of the pinned plane, which is the stronger metaphor for a
lattice cursor. The six view keys move to the number row (section 3).

- `8 2 4 6` = up / down / left / right within the pinned plane.
- `7 9 1 3` = the four diagonals within the plane.
- `5` = depth: one layer deeper (into the screen); `Shift+5` = one
  layer shallower (toward the camera). Section 4.
- Arrow keys = the cardinal four (mirror of `8 2 4 6`).

Movement is **screen-relative**, derived from the pinned view's basis
(table below), never raw grid axes: without this, Back vs Front and
Left vs Right silently mirror the keypad (Codex; correctness, not
polish). The plane and depth axes are derived from the pinned direction
on every move; nothing stores them, so they cannot desync (Grok).

Boundary (ruling, Q6): **clamp, never wrap.** On sparse grids a step
travels along the move vector to the next occupied cell; at the edge it
no-ops. The cursor never lands on empty space.

### 3. Axis view shortcuts (the depth solver by rotation)

Number-row keys re-pin the camera to the six orthographic views,
matching Blender's key semantics relocated off the numpad:

- `1` Front, `3` Right, `7` Top; `Ctrl+1` Back, `Ctrl+3` Left,
  `Ctrl+7` Bottom. (`keymap.ts` already distinguishes number row from
  numpad via `code`/`location`; the Ctrl variants land in the combo
  table, which today only carries undo/redo.)

The selected cube stays selected across a re-pin.

In any pinned view, two grid axes are in-plane (numpad-reachable) and
one is depth. Re-pinning makes the unreachable axis in-plane, so depth
is never a special direction: rotate the problem 90 degrees until the
axis you want is flat, then arrow. Reaching the buried center:

1. Front view. Arrow to the center of the face. Sets X=1, Y=1.
2. Press Top (or Left). Z is now in-plane.
3. Arrow once into the grid. Z=1. Center selected.

Every cube is reachable this way because each axis is in-plane in two
of the six views. Note (Codex correction): a re-pin can bury the cursor
*before any depth press*: the front-center cube is occluded by the top
layer the instant Top is pinned. So the rotation path needs buried-
cursor legibility too. In v1 that is the always-on-top cursor chrome
(section 5); the active-slice reveal (section 4) is the fast-follow
that upgrades it.

#### The six-view basis table

World axes, three.js Y-up; up vectors match the existing
`createCameraUp` convention (`viewportFocus.ts`). Implementation must
verify the grid-axis-to-world mapping against `createSceneGridLayout`
before hardcoding signs.

| View | Camera offset | Screen right | Screen up | Depth-in (`5`) |
| --- | --- | --- | --- | --- |
| Front | +Z | +X | +Y | -Z |
| Back | -Z | -X | +Y | +Z |
| Right | +X | -Z | +Y | -X |
| Left | -X | +Z | +Y | +X |
| Top | +Y | +X | -Z | -Y |
| Bottom | -Y | +X | +Z | +Y |

### 4. Dedicated depth in/out and the active-slice reveal

A dedicated key pair steps the selection along the current view axis,
one layer per press.

**Binding (Stuart's ruling, Q4, superseding both lane candidates):
`5` = in (deeper, into the screen); `Shift+5` = out (toward the
camera).** The numpad becomes a complete 3D controller: the eight
outer keys move within the pinned plane, the center key punches along
the depth axis perpendicular to it. Universal across keyboards, since
the logical `5` exists on the number row too. Both lane candidates
fall away: the wheel stays zoom (reserved in every reference tool),
and Q/E, PageUp/PageDown are not needed.

**Documented exception:** on the center key only, Shift means
*reverse direction*, not extend. This deliberately sacrifices one-key
shift-extend along the depth column: planar region-building is the
common case; depth-column extend is niche and deferred.

Implementation notes: Shift+Numpad5 is unreliable under NumLock on
some OSes, so bind on the logical `5` (including number-row `Digit5`),
never the numpad scancode alone. The on-screen keypad legend must
reconcile: `5` still visually marks "you are here" on the plane, but
the key drives depth; the pad has to show that.

**The active-slice reveal** (renamed from "see-through fade"; Codex:
Blender "x-ray" is a whole-scene toggle and Fusion "Select Through" is
a selection filter; ours is neither). **Status (Stuart's ruling):
fast-follow, not in the v1 gate.** The v1 ship bar covers buried-cursor
legibility with the always-on-top cursor chrome (section 5); the reveal
is the post-ship polish that adds spatial context around the cursor.
Scope when it ships (ruling, Q5, Opus):
**derived, never stored.** Layers forward of the active slice along the
view axis fade iff the active slice is not the frontmost occupied slice
in the pinned view; a pure function of (pinned axis, cursor depth),
re-evaluated on every re-pin and depth step. The fade appearing *is*
the "you are below the surface" feedback. It fires on re-pin burial as
well as depth-punch (the Codex correction above).

Render mechanics (Grok): a render-time display-opacity overlay only.
It never writes `face.state.opacity`; burial and exposure semantics
depend on authored `opacity === 1`. Faded faces leave the opaque
bucket (`depthWrite: false`), scoped to SELECT mode. Visibility-only:
faded cubes stay pickable; no raycast changes, no touch to the
drawn==picked invariant.


### 5. Real selection highlight color

Ruling (Q8): **chrome-only, via the token, two levels.**

- The render site is `CubeSelectionChrome` (composed through
  `CubeCellChrome` in `CubeScene.tsx`); the color is
  `polarity.selection <- themeColorTokens.selectionAccent`, today grey
  `#9a9a9a` (`themeTokens.ts:3`). Swap to Blender-family orange
  (~`#ED7000`, tuned live).
- **Two-level highlight (Codex, folded as requirement):** Blender
  distinguishes active (lighter) from other-selected (orange). With
  Shift+move extending a set, one color loses the cursor inside the
  set. Two tokens: `selectionAccent` for set members,
  `selectionActiveAccent` (brighter) for the active keyboard cursor.
- Chrome is **load-bearing, not polish** (Grok): after face culling a
  fully buried cube draws zero faces, so face tint or emissive cannot
  mark the center. No emissive fill in v1.
- **Buried legibility, v1 (Stuart's ruling):** the active cursor's
  chrome renders with `depthTest: false`, so the orange bracket always
  draws on top, buried or not. Member chrome keeps `depthTest` on.
  This is the ship-bar mechanism; the active-slice reveal upgrades it
  post-ship with spatial context. Chrome stays independent of cube
  material throughout.
- Applies in both ORBIT and SELECT; it is a general
  selection-legibility fix this feature forces but is not scoped to
  SELECT. No conflict with face-culling or drawn==picked because the
  treatment never touches cube geometry or picking.

## Selection semantics (how nav routes through existing state)

Keyboard moves are selection writes and MUST route through the existing
commit path, not a new one. Verified against the live store:

- **Respect `pickMode`** (`cube | face | edge`). v0.1 gates nav
  commands on `editor.pickMode === 'cube'` (ruling: cube-first
  confirmed; face/edge nav is a fast-follow).
- **Plain move = replace**, via `ports.selection.setSelection`:
  non-history, collapses any multi-set, consistent with the shipped
  ephemeral model (`cubicellStore.ts` setSelection).
- **Shift+move = extend**, via the existing `select-toggle` command
  path (`toggleSelection` -> `commitSelectionEditor` ->
  `pushAssemblyMutation`), feeding the ephemeral assembly exactly as
  shift-click does. No second commit semantics. One documented
  exception: on `5`, Shift reverses depth direction instead
  (ruling 4).
- Moves dispatch as registered commands so palette and keymap come
  free; no direct store pokes.

## Keymap architecture (ruling, Q9)

One resolver, mode-aware, no parallel keymap:

- The mode branch lives **only** in `getKeyboardShortcutCommandId`:
  a thin SELECT override table (~15 keys) consulted first,
  `selectOverride[key] ?? base[key]`; the ORBIT base tables are
  untouched.
- **Gotcha (Opus):** the numpad resolves through TWO paths, the code
  table (`keyboardCommandIdsByCode`) and the location fallback
  (`getNumpadKeyCommandId`, `keymap.ts:151`). The override must
  intercept both or nav leaks to orbit.
- `getKeyboardShortcutRepeatId` stays mode-independent: it identifies
  the physical key, and threading mode into it would break held-key
  release tracking.
- Shift handling: Shift+move (extend) and Shift+5 (depth reverse) are
  the first bare-key Shift bindings; the resolver gains SELECT-scoped
  shift variants, with `5` resolving by logical key (numpad and
  `Digit5`) per ruling 4.
- The on-screen keypad (`viewControlDefinitions.ts` hardcodes
  `viewOrbit*` ids) must resolve through the same mode-aware source,
  or the pad lies in SELECT (Grok).

## Rulings (all 10 open questions closed)

1. **Mode home:** new `editor.navMode`, session-only, boots ORBIT
   (Stuart). Undo-exclusion free; no persistence wiring.
2. **Re-pin target:** nearest axis, on entry and on every re-pin.
3. **Projection:** force ortho on entry, restore prior on exit;
   capture in `editor.navPriorProjection`; a manual P inside SELECT
   drops the capture.
4. **Depth binding:** `5` in / `Shift+5` out (Stuart). Shift reverses
   direction on the center key only, a documented exception to
   Shift=extend; depth-column extend deferred. Wheel stays zoom.
5. **Reveal scope:** fast-follow, not in the gate (Stuart); v1 buried
   legibility is the always-on-top cursor chrome. When it ships:
   derived, fires iff active slice is not frontmost; covers re-pin
   burial; never a stored toggle.
6. **Boundary:** clamp, never wrap; sparse grids step to next occupied
   cell along the vector; never select empty space.
7. **Cursor seed on empty selection:** the prior active selection if it
   survives reconcile; else the occupied cell nearest the viewport
   center on the frontmost occupied slice of the pinned view; never
   empty space.
8. **Highlight:** chrome-only token swap to orange, two levels (member
   vs active cursor), no emissive v1; chrome load-bearing post-culling.
9. **Keymap:** single resolver with SELECT override table; both numpad
   paths intercepted; repeatId untouched; keypad shares the resolver.
10. **Diagonals off-numpad:** cardinal-only on laptops in v0.1.
    Shift+Arrow already means extend and cannot also encode diagonals;
    numpad remains the power path.

## Non-goals (v0.1)

- Not the query-authoring surface (verbs, chips, predicates). That is
  the separate proposal; this is the pointer-replacement layer beneath
  it.
- Not face/edge keyboard navigation (cube-first; fast-follow).
- Not box/marquee selection; the reveal is visibility-only, not a
  selection gesture.
- Not saved/named selections.

## Slice plan (Grok's sizing, amended)

Each slice independently shippable, cheapest first:

| Slice | What | Size |
| --- | --- | --- |
| A | Orange chrome tokens (two levels) + `depthTest: false` on the active cursor's chrome. Independent; do first | 0.5d |
| B | `editor.navMode` + tab + orbit-gesture auto-return | 1d |
| C | Six axis pins + nearest-axis entry + force-ortho/restore | 1.5-2d |
| D | Mode-aware keymap + plane-move/depth commands | 1.5d |
| E | On-screen keypad rebind through the shared resolver | 0.5d |
| F | Depth on `5`/`Shift+5` (logical-key binding, pad legend) | 0.25-0.5d |
| G | Active-slice reveal (fast-follow, post-ship polish) | 1-1.5d |

The gate is **A-D, roughly 4.5-5.5 days** (Stuart's ruling): the
`depthTest: false` cursor chrome in slice A satisfies buried-center
legibility without the fade system, so Codex's re-pin-burial
correction is answered inside the gate. E, F, and G are post-gate
refinement; G is the named fast-follow.

## Ship bar

A human can select the buried center cube of a 3x3x3 from the keyboard,
see it clearly highlighted while it is buried (the always-on-top cursor
chrome), and the move participates correctly in single-select
(non-history) and shift-extend (ephemeral assembly) semantics.
Everything past that (depth-punch convenience, the active-slice reveal,
face/edge nav, keypad rebind) is refinement, not the gate.

## Grounding (existing surfaces this rides)

- `src/state/cubicellState.ts` — editor session (`pickMode`, `mode`);
  new `navMode`, `navPriorProjection` land here; session is neither
  persisted nor in history.
- `src/state/cubicellStore.ts` — `setSelection` (plain move),
  `toggleSelection` (extend), `applySelectionResult`; view-lane
  `recordHistory: false` precedent.
- `src/state/selectionCommit.ts`, `selectionAssembly.ts` — the commit
  and ephemeral-assembly path every move uses.
- `src/editor/keyboard/keymap.ts` — the resolver to make mode-aware;
  both numpad paths; combo table for Ctrl view keys.
- `src/pose/focusView.ts` — `FocusViewOrientation` direction form: the
  absolute pin mechanism.
- `src/camera/orbitDetent.ts` — ORBIT-only; not the pin mechanism.
- `src/camera/cameraGestureRuntime.ts` — gesture boundary for
  auto-return.
- `src/editor/commands.ts`, `affordances.ts` — registration for nav,
  axis-view, and depth commands.
- `src/scene/CubeSelectionChrome.tsx`, `src/theme/themeTokens.ts:3`,
  `src/theme/scenePolarity.ts:93` — highlight site and tokens.
- `src/controls/view/viewControlDefinitions.ts` — keypad to route
  through the shared resolver.
- `src/view/viewportFocus.ts` — `createCameraUp`, framing.

## Delta ledger

- **v0.1 -> v0.2 (this fold):** Stuart's session-only navMode ruling
  (Q1); Grok's orbitDetent correction (relative stepper, not absolute
  snap; pins ride `FocusViewOrientation`), highlight site and token
  trace, chrome-as-load-bearing post-culling, reveal render mechanics
  (display-opacity overlay, never authored opacity), sparse-grid
  clamp rule, gesture-hook and derived-axes couplings, slice sizing;
  Opus's navMode home confirmation, projection capture/restore with
  the manual-P edge, derived reveal condition, keymap override
  architecture with the dual numpad-path gotcha; Codex's prior-art
  honesty (two-view positioning is established, the cursor is ours),
  Blender numpad key-reference correction and the deliberate-remap
  framing (plane on numpad, views on number row with Ctrl opposites),
  six-view basis table with screen-relative movement as correctness,
  re-pin-burial correction (reveal joins the ship bar; the "rotation
  path never needs fade" claim deleted), "active-slice reveal" naming,
  two-level highlight requirement, deletion of the absolute
  "every reference tool" claim; depth-key conflict closed by Stuart's
  ruling, `5` deeper / `Shift+5` shallower (numpad as complete 3D
  controller; Shift-reverses-on-center documented exception;
  logical-key binding for NumLock safety; pad legend reconciled),
  superseding Grok's Q/E-plus-wheel and Codex's PageUp/PageDown.
- **v0.2 -> v0.3 (Stuart's ship-bar ruling):** the active-slice reveal
  demoted from gate to fast-follow; v1 buried-cursor legibility is the
  always-on-top (`depthTest: false`) active-cursor chrome, folded into
  slice A; gate revised back to A-D (~4.5-5.5d); the pick-vs-bloom
  boundary with the select-ux proposal stated (numpad nav reaches the
  exemplar, verbs expand it; Shift+numpad by-hand, verbs by-rule).
