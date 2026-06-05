# Face mark: the authoring angle

Scout report, feat/face-mark, base main 7d5e942. Question: how does a person actually author a mark on a face. Read-only survey of the worktree; both assets rendered from their paths.

## The assets, as an author sees them

**helioy.svg**: two coarse paths, positive black form on empty ground, its own margin inside a 250-square canvas. Forgiving: near-symmetric, no fine detail, figure is the painted region, ground is nothing.

**manicure.svg**: a 214-square black field covering the full canvas with a face carved out of it, bleeding off two edges, plus two small positive paths (right eye, nose) floating inside the carve. The identity lives in the carved boundary and eyelash-width detail. The painted region is the *field*; the face reads because of what is not painted.

These two are opposite answers to every authoring question: figure (form vs field), fit (margin vs bleed), and what a polarity swap does to them.

## 1. Smallest authoring surface

Four enum rows, all riding the existing control-binding machinery. Zero new interaction patterns, zero new panels.

| Binding | Options | What it authors |
|---|---|---|
| `face.mark` | None, Helioy, Manicure, … | which form, from a closed mark registry |
| `face.markFigure` | Form, Field | which region is figure: the painted region or its complement |
| `face.markColor` | Theme, Black, White, Accent | the figure's colour role — this **is** the polarity pin |
| `face.markFit` | Margin, Bleed | contain vs cover |

Why this is sufficient, and why most of it already exists:

- **The Color control's derivation move is the template.** `partColorOptions` derives its enum from the closed `cubePartColors` vocabulary (`src/editor/controlBindings.ts:120`, vocabulary at `src/domain/cubeEdgeState.ts:6`). `face.mark` derives the same way from a mark registry. For v1 the registry is build-time (the two owner marks), which keeps the schema static; see the caveat in §2.
- **Figure/ground pinning needs no new concept.** The colour vocabulary already distinguishes rail-following from pinned: `theme` resolves through the polarity rail to `polarity.contrast` (`resolveCubePartColor`, `src/theme/scenePolarity.ts:38`), while `black`/`white`/`accent` are fixed hexes per polarity family. So "pin the negative mark against polarity swaps" is literally `face.markColor = black` instead of `theme`. The accent-colour work that just landed (7d5e942) made this vocabulary exhaustive per polarity; the mark rides it as-is.
- **Ground is not a new control.** The mark partitions the face into two regions; the figure region takes `face.markColor`, and the ground region stays the face's existing `face.color`. Authoring manicure: mark=Manicure, figure=Field, colour=Black (pinned), fit=Bleed. Authoring helioy: mark=Helioy, figure=Form, colour=Theme (rails), fit=Margin. Two faces, two opposite mark grammars, same four rows.
- **State and persistence ride the face state.** `CubeFaceState` is `{color, opacity, visible}` (`src/domain/cube.ts:36`); the mark fields append with defaults (mark=none). The pose codec constraint is already documented at the vocabulary ("appended, never reordered", `src/domain/cubeEdgeState.ts:4`). Writes go through the existing `set-face-state` patch command — no new command kind, which honours the CUBICELL.md contract that everything enters through the command bus as serializable state.

Import is deliberately **not** part of this surface. No file-import interaction exists anywhere in the app today (no file input, no FileReader, no drop target — verified by search), so an import UI would be the one genuinely new surface. Decouple it: v1 ships the registry with the owner's marks compiled in; when import arrives later it is a scene-level command (marks become scene assets, normalized at import) and the four face rows do not change. The authoring surface is stable across that transition.

## 2. Where it lives

The face already has a styling home, mounted in two places, and both come for free:

- **Binding owner**: `src/editor/controlBindings.ts` — `faceColorBinding` (line 364) is the exact template; new bindings append to `controlBindingList` and the `ControlBindingId` union.
- **Panel definition**: `src/panels/panelDefinitions.ts` — `faceBindingIds` (line 21) currently `face.visible | face.color | face.opacity`; the mark rows append here.
- **Section owner**: `FaceSection` in `src/panels/PartSection.tsx:24` — face part picker plus the binding fields.
- **Hosts**: the Inspector's face pick-mode tab (`src/panels/Inspector.tsx:68`) and the Selector's MODIFY tab (`src/panels/SelectorPanel.tsx:117`, `ModifyTab`). Both mount `FaceSection`, so the mark rows appear in both without either being touched.
- **Field renderer**: `ControlBindingField` (`src/panels/ControlBindingField.tsx:14`) renders enum schemas as `Segmented` rows — the mark rows are Segmented for free, matching every other face control.
- **Later, for import**: `SceneSection` (`src/panels/SceneSection.tsx:15`) in the left rail's scene tab is the scene-level home if marks become imported scene assets on `CubicellScene`.

One honest seam: `ControlBinding.schema` is a static property (`src/editor/controlBindings.ts:70`), and `ControlBindingField` reads `binding.schema.options` directly. A build-time mark registry keeps that true. The day marks become scene data, enum options must derive from `ControlBindingContext` — a small, contained extension (schema or options as a function of context), but it is the one place the machinery does not already bend.

## 3. What selection means

Face selection is first-class and the mark inherits its whole grammar:

- `CubePartSelection` `{cubeId, kind: "face", partId}` (`src/domain/selection.ts:10`). The Inspector's pick-mode tabs and the in-panel face picker both produce it; shift-click toggles homogeneous multi-sets (`toggleSelectionInSet`, `selection.ts:195`).
- **Multi-face application is not merely coherent — it is already the write path.** Every face binding writes `set-face-state` with `scope: resolvePartEditScope(...)` (`controlBindings.ts:78`), so when the edit target is the selection set, the patch stamps every selected face. `face.color` behaves exactly this way today; `face.mark` is the same stamp with more fields. `SelectionEditTargetToggle` in the Selector's MODIFY tab already gives the author the part-vs-set choice.
- **The query builder makes multi-apply the point.** `FaceSelectionBuilder` (`src/panels/FaceSelectionBuilder.tsx:53`) builds directional face queries — "all front faces", filtered to exposed. "Select every exposed front face, stamp Helioy" is a two-gesture brand pass over a whole composition. This is the strongest argument that the mark belongs on the existing face grammar rather than a bespoke surface.
- Mixed-state reads follow precedent: `binding.read` reports the active face's value (`getSelectedFaceState`, `controlBindings.ts:94`), same as `face.color` on a mixed set; `cube.color` shows "mixed". Nothing new to invent.
- The one selection path to treat with care: pick-mode conversion expands a cube to all six faces (`convertSelectionToPickMode`, `selection.ts:246`). Stamping a mark on six faces at once is legal and cheap — and is exactly where the orientation problem below becomes visible.

## 4. The honest UX risk

**Orientation.** The smallest surface has no rotate or mirror control, and a mark, unlike a colour, has an up and a handedness. Each of the six faces needs a UV frame; "up" on the front face is not "up" on the top face, and opposite faces are mirror-related when both are drawn to be read from outside. helioy survives this — it is coarse and nearly symmetric. manicure is a face in profile: sideways it is wrong, mirrored it is *differently* wrong, and the eye knows within a second. The first live test will be "put manicure on a side face," and with any naive UV assignment it will fail that test. This is the killed-feature shape: every automated gate passes, the hand says no.

The smallest honest countermeasure is not a control, it is a decision: fix one per-face UV convention deliberately (screen-readable, world-up projected per face, opposite faces un-mirrored), verify it by hand on all six faces with manicure before the surface is judged, and hold a 4-step rotation enum (0/90/180/270) in reserve as the first escape valve if the convention fails. Do not ship a free-angle control; that is appearance authoring creeping in through the back door.

Two secondary risks, named so they are chosen rather than discovered:

- **The polarity flip moment.** If a mark's colour defaults to `theme`, flipping the scene polarity switch inverts manicure's field from black to white in one gesture. The pin exists (§1), but the default decides the feel: an author who has not yet learned to pin will read the inversion as breakage of their brand, not as the rails working. The default for the mark colour role deserves an explicit decision, possibly per-figure (Field defaults pinned, Form defaults theme).
- **Workbench tonal compression.** The workbench remaps black/white into a compressed range and applies a per-face lightness ramp (`workbenchPartColorsByPolarity`, `cubeFaceLightnessDeltaById`, `src/theme/scenePolarity.ts:63,10`); artifact configs carry neither. For plain colour fields the drift is acceptable; for a logo whose entire job is contrast legibility, what the author tunes by eye on the workbench is not exactly what exports. Worth one deliberate hand-check of a marked face in workbench vs export before calling authoring done.

## Summary

The authoring surface is four Segmented enum rows appended to `faceBindingIds`, written through `set-face-state`, hosted by the existing `FaceSection` in both the Inspector and the Selector, with figure/ground pinning expressed entirely through the existing closed colour vocabulary. The only genuinely new UI (import) is deferrable without changing the surface. The thing to fear is not the surface — it is orientation, which no gate will catch and the owner's hand will.
