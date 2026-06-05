# Cubicell Colour UX Brainstorm (ux-designer)

## Proposal

**Roles, not swatches. Colour is a keyframe-scoped palette mapped over the existing part-role vocabulary.**

The codebase already authors colour as a role, not a value: `CubePartColor = "theme" | "black" | "white"` (`src/domain/cubeEdgeState.ts` `cubePartColors`), resolved at render time through `resolveCubePartColor` against a `ScenePolarityConfig.partColors` table (`src/theme/scenePolarity.ts`). Polarity is a two-entry palette wearing a different name. The proposal is to widen that table, not replace the architecture:

1. Add one (max two) chroma-carrying roles to the part vocabulary: `"accent"` (optionally `"accent2"`). A part is authored as theme / black / white / accent, exactly like today.
2. Add a **Palette** to the Pose (`src/domain/scene.ts` `CubicellScene`, beside `polarity`): it defines what each role resolves to. Default palette reproduces today's output byte-for-byte.
3. Constrain accent colours in OKLab: **hue and chroma are free, lightness is pinned** near the polarity pole the accent replaces. This is the direct answer to the failed #160/#162 direction. Lightness already carries authorship meaning; colour must arrive on the orthogonal channels (hue, chroma), never by spending lightness. The picker for an accent is therefore two scrubs (hue, chroma), not a colour wheel, and mid-grey ambiguity is structurally impossible.

**Position on the standing thesis** ("colour is a function of coord and time, not a picked swatch"): half right. Right about the control surface — one control must restyle a thousand cubes coherently, and the palette does exactly that. Wrong about the substrate. A pure coord function takes authorship away: a cube is black because the owner said so, and colour-by-coordinate erases that intent the same way lightness-by-orientation did. Bind functions to the **role→colour mapping** (e.g. a preset where accent hue drifts along X, or across time), not to per-face colour. The function becomes an optional modulation inside the palette, and the guarantee survives: coherence comes from role scarcity (≤2 accents), not from banning authorship.

**Position on the open decision**: the look belongs to the **keyframe**. Precedent is already set: `polarity` lives in `Pose`, a State capture snapshots it (`src/panels/stateCapture.ts` `createStateCapture` → `poseRevision`), and `Keyframe.stateId` (`src/domain/score.ts`) makes it transitionable. Put the palette in `Pose` and a look change is animatable across a State transition for free, via the existing OKLab tween (`src/scene/colorSpace.ts` `resolveLerpedPartColor` / `PartColorTween`; it needs a from/to polarity-config pair instead of one, a small signature change). A document-level look would be new machinery with no transition story. Document-level is the wrong default; a "apply this palette to all States" verb covers the "I want it everywhere" case without changing ownership.

## Authoring Flow

Target: colour on a piece in under a minute, zero per-cube pickers.

1. **First run.** User opens the left rail **Scene** tab (or a fourth `Look` tab, see Open Questions). Below the existing Polarity switch sits a **preset row**: 5–7 chips. Each chip is a live thumbnail of *the user's actual scene* rendered with that palette — `src/thumbnail/thumbnailRenderer.ts` `createOrthographicThumbnailRenderer` already renders any `Pose` headlessly, so a chip is `render({...pose, palette: candidate}, axis)`. Not abstract swatch strips; your composition, restyled. One click applies. This is the whole first-minute experience.
2. **Marking parts.** To decide *which* parts carry the accent, the user uses the controls they already know: the Inspector Face/Edge **Color** enum (`src/editor/controlBindings.ts` `partColorOptions`, consumed by `faceColorBinding` / `edgeColorBinding`) grows one option: Theme / Black / White / **Accent**. Scope is already legible there: single selection edits the part, a selection set shows the existing Part / Set toggle (`src/panels/SelectionEditTargetToggle.tsx`), and `resolvePartEditScope` (`src/editor/controlBindings.ts`) resolves it. Nothing new to learn. Presets can ship with a default role assignment rule (e.g. "accent = all black faces") so step 1 alone already shows colour.
3. **Tuning the look.** Disclosure below the preset row, ordered by impact:
   - **Hue** scrub (0–360, wraps) — `src/components/ui/scrub-field` `ScrubField`, the app's native idiom. Dragging it live-restyles every accent part at once. This is the "one control, thousand cubes" moment.
   - **Chroma** scrub (0–max-gamut for the pinned L; clamp via the existing `setOklabToLinearSrgb` gamut clamp in `src/scene/colorSpace.ts`).
   - **Accent 2** (if approved): a second hue/chroma pair, revealed only after the first accent is in use.
   - **Advanced / Drift**: the coord-and-time function, as a palette modulation — e.g. hue offset per X index, or hue rotation per second. `Segmented` for the axis, `ScrubField` for the amount. Off by default.
4. **Scope legibility rule.** Two panels, two scopes, no overlap: *what role a part plays* is selection-scoped and lives in the right-rail Inspector (existing Color enums); *what the roles look like* is keyframe-scoped and lives in the left rail. The left-rail panel header states the scope explicitly: "Look — this State". No control ever applies to an ambiguous middle.
5. **Animating the look.** Capture State A, change hue, capture State B — the transition tweens accent hue in OKLab through the existing `StateTransitionTrack` machinery. No new timeline UI.
6. **Presets and parameters coexist** by the standard "preset = named parameter bundle" contract: touching any scrub detaches to "Custom" (chip row shows no selection); re-clicking a chip re-bundles. Presets are starting points, never a mode.

## Reuse (path + symbol)

- `src/domain/cubeEdgeState.ts` — `cubePartColors`, `isCubePartColor`: the role vocabulary to extend.
- `src/theme/scenePolarity.ts` — `ScenePolarityConfig`, `resolveCubePartColor`, `createPolarityConfig`: the role→colour resolution seam; palette slots in here.
- `src/theme/themeTokens.ts` — `themeColorTokens`: token home for shipped preset values.
- `src/scene/colorSpace.ts` — `resolveLerpedPartColor`, `resolvePartColor`, `setOklabToLinearSrgb`: OKLab resolve/tween/gamut-clamp, all present.
- `src/domain/scene.ts` — `CubicellScene.polarity`, `poseFromScene`: precedent and home for `palette` on the Pose.
- `src/domain/cubeOperations.ts` — `CubeOperation "set-cube-color"`, `"set-face-state"`, `"set-edge-state"`, `CubeScope`: role assignment ops exist; no new op kind needed for marking parts.
- `src/editor/controlBindings.ts` — `partColorOptions`, `faceColorBinding`, `edgeColorBinding`, `scenePolarityBinding` (`"scene.polarity"`), `resolvePartEditScope`: binding pattern to follow for `scene.palette.*` bindings.
- `src/panels/SceneSection.tsx` — Polarity `Switch` row: insertion point for the Look block (or sibling tab in `src/panels/LeftRail.tsx` via `leftRailTabs` in `src/state`).
- `src/panels/ControlBindingField.tsx`, `src/panels/useControlBinding.ts` — generic bound-field plumbing.
- `src/components/ui` — `ScrubField`, `Segmented`, `Switch`, `Button`: complete control kit; no new primitive required except the preset chip.
- `src/thumbnail/thumbnailRenderer.ts` — `createOrthographicThumbnailRenderer`; `src/thumbnail/thumbnailArtifact.ts` `createThumbnailArtifact`: live-scene preset chips.
- `src/panels/stateCapture.ts` — `createStateCapture`; `src/domain/stateTransition.ts` — `StateTransitionTrack`: keyframe ownership and transition ride-along.
- Prior palette/preset/colour-picker UI: **none found**. Searches run from repo root: `grep -rln "palette\|swatch\|Palette" src/` (one comment in `src/editor/commands.ts:269`, no code); `grep -rln "preset" src/` (only `renderPixelRatioPreferences`-adjacent and `GridPreset` in domain, no UI preset system); `grep -rln "hue\|chroma\|oklch" src/` (only `src/scene/colorSpace.ts` math).

## What I Would NOT Build And Why

- **A per-cube colour picker.** Direct threat to the under-a-minute guarantee; makes incoherent results the easy path; explicitly flagged in the brief. The Accent enum option gives per-part control without ever exposing a value picker at selection scope.
- **Anything that spends lightness.** Rejected live (#160, #162). All accent lightness is pinned; tint/shade sliders, per-face ramps, and AO stay dead.
- **A free colour wheel / hex input.** Off-idiom (the app is scrub-and-segmented) and it reopens the lightness channel. Hue+chroma scrubs over a pinned L are strictly safer and faster.
- **Unlimited palette roles.** Coherence is a function of scarcity. One accent by default, two maximum. More roles converts the palette into a picker with extra steps.
- **A document-level look system.** No transition story, contradicts the owner's keyframe lean, and duplicates what Pose ownership gives for free. An "apply to all States" verb is the honest version of this need.
- **A pure coord-function colouriser as the primary surface.** It demos well and authors badly: it overrides the owner's black/white intent wholesale. It survives only as an optional drift modulation inside the palette.
- **A new panel framework or chip carousel component.** The preset chip is one small component over the existing thumbnail port; everything else reuses the control kit.

## Open Questions For The Owner

1. **One accent or two?** One keeps the model trivially coherent; two enables complementary schemes. Recommend shipping with one and reserving the slot.
2. **Do edges get accents, or faces only?** Edges are the seam identity (hard black/white). Colouring seams may dilute the graphic signature. Recommend faces only in v1; `edgeColorBinding` makes edges a config flip later.
3. **Does Polarity fold into the palette** (a palette defines background + both poles + accents) or stay a separate switch above it? Folding is cleaner conceptually; the standalone switch is a beloved fast toggle. Recommend keeping the switch as a shortcut that flips the palette's polarity field.
4. **Left rail placement:** grow the Scene tab or add a fourth `Look` tab to `leftRailTabs`? Depends on how large the disclosure stack gets after the preset row.
5. **Preset curation:** who authors the shipped palettes, and are user-saved palettes (library asset, like Structures) in scope for v1? Recommend shipped-only in v1.
6. **Does the drift modulation (coord/time hue offset) land in v1**, or is v1 preset row + hue/chroma scrubs only? Recommend deferring drift; it is additive and the palette schema can reserve the field.
7. **Export fidelity check:** artifact configs carry no `edgeLightnessDelta` so exports show authored colours exactly (`src/theme/scenePolarity.ts`); confirm accents follow the same rule — workbench may remap tonally (`workbenchPartColors`), export never.

## Consensus Round

**A. Pole concession: `concession`.** The visual-designer's gamut table settles this with arithmetic: L=1.0 holds exactly zero chroma and #050505 nearly none, so "colour without moving the poles" is not a design option, it is a contradiction. The concession is acceptable because it is *scoped by authorship*: only parts assigned the accent role move to the rails (L 0.22 / 0.93); parts authored `black`/`white` stay exact #050505/#ffffff, and a composition with no accents is byte-identical to today. 14.3:1 worst case is still emphatic contrast, and mixed pure-vs-tinted pairs measure higher (17:1), so mixing is safe. If the owner rules the poles inviolable even for opt-in parts, then edges and field are the whole menu and faces stay neutral — that ruling gates everything, which is why this fork is first.

**B. First surface: `faces`.** I hold my position against Axis Ink-first. Edges are thin: at composition zoom an edge-only palette reads as "black and white cubes with faintly coloured wires", which does not answer the owner's actual complaint ("needs more than black and white cubes") and risks a flat live verdict that discredits colour wholesale. The product value is on faces, where colour is visible. The visual-designer's real argument for edges is risk containment, and I take that seriously — but the containment I trust is authorship containment (accent is opt-in per part, default scenes untouched), not surface containment. His own discipline rule ("one surface at a time") I adopt: faces only in v1, edges deferred behind a config flip on `edgeColorBinding`.

**C. Vocabulary: `enum`.** Closed role vocabulary, one new label (`accent`), resolved through the existing polarity table. The persistence facts make freeform strictly worse: `compactPose.ts` encodes colour as an index into `cubePartColors`, `PartColorTween` carries discrete labels, and `ScenePartColors` keys are the role set — freeform sRGB literals invalidate all three and require a parallel value shape. But the decisive argument is product, not plumbing: freeform is a per-part colour picker by another name, and the picker is the named threat to the under-a-minute guarantee. Coherence must be structural (few roles, one mapping) rather than a user achievement. I reject the frontend-engineer's "add validated sRGB literals as value strings" substrate on these grounds; his own cost table shows the enum path is also the cheapest.

**D. Authorship vs function: `authorship`.** A coord function that writes per-face colour erases the owner's black/white intent exactly as orientation-driven lightness did — same failure class, different channel. The function survives as a *modulation of the role→colour mapping*: Axis Wash becomes "accent hue drifts along X", Enclosure Chroma becomes "accent chroma keys to burial" — both expressible as palette parameters over parts the owner marked, neither able to touch a part the owner left pure. This also sidesteps the visual-designer's own performance warning: per-frame CPU colour functions rewrite every instance every frame, while role-mapping changes are sparse patch-driven writes through the existing `changedAttributes` path.

**E. Product-value ranking.**
1. **Accent Role** — authored meaning plus one-control coherence plus free animatability (palette in Pose rides State transitions).
2. **Axis Ink** — safe and real, but low visual yield; right as a follow-on surface, wrong as the opening statement.
3. **Field Tint** — cheap ambience, zero risk, zero authorship; a garnish.
4. **Axis Wash** — high demo value, but as a per-face function it fails D; admitted as an accent-role drift modulation, it merges into 1.
5. **Enclosure Chroma** — information display, not composition; same modulation caveat, plus burial depth is genuinely new domain work.
6. **Facet Hue** — the rejected mechanism's shape with hue swapped in; the visual-designer concedes it delivers facet separation, not modelling, and per-face hue variation is the most likely candidate to reproduce the "confusing to look at" verdict.

**First slice for the owner: Accent Role on faces.** One sentence of value: *mark parts as accent, drag one hue scrub, and the whole piece restyles coherently — and because the look lives in the keyframe, it tweens across State transitions with machinery that already exists.*

**F. Grooming ride-along: consolidate face colour onto the field-owner pattern.** The accent slice widens `cubePartColors`, which moves the wire shape — exactly the moment the scout's recommendation fires: face colour encode/morph/impact are hand-rolled beside `cubeEdgeStateOwner`, and widening the type through two ownership styles deepens the split. Fold face colour onto the field-owner pattern in the same change set, and derive `partColorOptions` from `cubePartColors` while touching it (removes the hand-synced list the slice would otherwise extend by hand). **Defer:** the `themeTokens.ts` / `tokens.css` hex dual (real debt, zero coupling to this slice) and any reversal of #160's `cubeFaceLightnessDeltaById`. The scout's finding that the face ramp mutates artifact and thumbnail paths means exports do not show authored colours today — that must be *flagged to the owner as a fidelity decision*, not silently reversed inside a colour PR.

**Discipline.** (1) Changed: my original spec said accent lightness is "pinned near the polarity poles", implying colour could sit at or beside the authored extremes; the visual-designer's measured gamut table showed the poles have no chroma capacity, so I now explicitly adopt the rail concession (A=concession) with pinned L *at the rails*, not near the poles. (2) Still reject: the frontend-engineer's recommended substrate of validated freeform sRGB literals (his Recommended Substrate §2) — it trades the structural coherence guarantee and the compact-index wire for flexibility nobody asked for, and it is the picker the brief names as a threat; and the visual-designer's "ship Axis Ink first" — proof-of-safety is the wrong first impression when the question on the table is whether colour makes the product better.
