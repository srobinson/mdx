# Scout: interaction core + command descriptor registry (MODEL.v2 extraction step 4)

Read-only scout, 2026-07-10, by cubicell:general:8:6.1. No source
modified. Basis: main at 06ba766 (steps 1-3 merged). This is design
input for a round with Stuart before any build; section 6 holds the
genuine forks. MODEL.v2 calls this registry "the spine of everything."

## 1. Scatter inventory

Five sites each encode one facet of a command. The union
(`EditorCommand`, `src/editor/commands.ts`) has nine kinds: `view`
(wrapping six `ViewCommand` kinds), `focus-toggle`, `scene`,
`capture-toggle`, `editor-mode-toggle`, `build-mode-toggle`,
`history`, `pick-mode`, `pick-mode-cycle`.

| Site | Home | Facet encoded | Coverage |
| --- | --- | --- | --- |
| `classifyCommand` (+`isAbsoluteViewCommand`) | `src/interaction/command.ts` | lane + view arbitration | `view` -> view lane, `focus`/`reset`/`restore` absolute vs additive; all else -> synchronous |
| `getEditorCommandId` + `getOrbitCommandId` / `getPanCommandId` / `getZoomCommandId` / `getPickModeCommandId` / `getSceneCommandId` (all private) | `src/editor/commandRegistry.ts` | command -> id reverse lookup by VALUE-matching payloads against preset step constants (`viewOrbitStepRadians` etc.), ~150 lines | all nine kinds |
| `getEditorCommandRepeatBehavior` (+`canRepeatViewCommand` in `commands.ts`) | `src/editor/commandRegistry.ts` | repeat facet (`none`/`discrete`/`hold`): history -> discrete, view orbit -> discrete, view pan/zoom -> hold, non-view -> none | all nine kinds |
| `runSynchronous` | `src/app/useSynchronousEditorCommands.ts` | the synchronous handler switch, one `if` per kind, plus the ONLY live precondition in the system (`capture-toggle` rejects with "No capture surface" when no recorder is registered — this is `canRun` avant la lettre) | 7 synchronous kinds + truthful fall-through rejection |
| `dispatchCoreCommand` (private) | `src/interaction/interactionCore.ts` | core enrichment: which commands need context injected before the bus (`focus-toggle` -> selection frame + saved pose; `view`/`reset` -> grid frame target) | 2 special cases + pass-through |

Load-bearing discovery: **the ~150-line reverse-lookup chain exists
only to serve `getEditorCommandRepeatBehavior`** (via
`getEditorCommandDefinitionForCommand`; nothing else calls it). The
public forward lookup (`getEditorCommandDefinition`, id -> definition)
has exactly two consumers, both healthy affordance surfaces:
`src/controls/view/viewControlDefinitions.ts` (keypad) and
`src/editor/keyboard/keymap.ts`. Make repeat behavior a kind-level
descriptor fact and the entire reverse chain becomes dead code.

Second discovery: today's `editorCommandDefinitions` (26 entries)
conflates two different things. `view.orbit.up` is not a command kind;
it is an **affordance binding** (id + label + preset params over the
`orbit` kind) for the keypad and keymap. The kind-level facts (lane,
target, repeat, handler) repeat across all 16 view bindings. The
registry finish should separate **kind descriptors** (nine today) from
**affordance bindings** (the 26 id-keyed presets), or the reverse
value-matching problem recreates itself.

## 2. Proposed descriptor shape

Keyed by union kind (the `EditorCommandDefinition` name stays for the
affordance list; the new table is the kind descriptor):

```ts
type CommandKindDescriptor = {
  kind: EditorCommand['kind']
  target: 'document' | 'view' | 'transport' | 'mode' | 'selection' | 'capture'
  lane: 'synchronous' | 'view'        // DEFAULT derived from target; declared here as the escape hatch
  arbitration?: 'additive' | 'absolute' | ((c: EditorCommand) => 'additive' | 'absolute')
  repeat: 'none' | 'discrete' | 'hold' | ((c: EditorCommand) => ...)
  canRun?: (ctx: CommandContext) => true | { reason: string }
  run?: (c: EditorCommand, ctx: CommandContext, ports: CommandPorts) => SynchronousDispatch
}
```

Phasing per MODEL.v2: `lane` + `arbitration` + `repeat` first (kills
`classifyCommand` + the repeat/reverse chain), `canRun` + `run` second
(kills `runSynchronous`'s switch and absorbs `dispatchCoreCommand`'s
special cases), `params` schema later when the LLM/actor surface
hardens.

Scope -> taxonomy mapping (today's `scope: capture|editor|scene|view`):

| Today | Commands | Taxonomy target | Note |
| --- | --- | --- | --- |
| `view` | 16 view bindings + `focus-toggle` | **View** | clean |
| `scene` | `camera.projection.toggle` | **Document** | settled by Slice 2; scene authoring stands |
| `editor` | `editor-mode-toggle`, `build-mode-toggle`, `pick-mode` x3, `pick-mode-cycle` | **Mode** | clean |
| `editor` | `edit.undo`, `edit.redo` | **Document via the History mechanism** | escape hatch needed: MODEL.v2 says History is a mechanism over Document, not a peer target; and history commands are not themselves undoable, so `target: document` + `reversible: false` must be expressible |
| `capture` | `capture.toggle` | **Capture (sink)** | clean; carries the system's one real `canRun` |

Gaps the mapping exposes (both are missing taxonomy rows in the
vocabulary, not mis-scopes):

- **Transport commands do not exist.** Play/pause/scrub/loop are store
  actions; `src/panels/BottomDock.tsx` writes `setTransportTime` /
  `setTransportPlaying` directly. The same "no privileged path"
  violation Slice A's spec documents for selection. MODEL.v2's
  taxonomy says Transport is actor-facing; an LLM cannot press play
  today. The descriptor `target: 'transport'` row is empty until a
  transport-command slice fills it.
- **Selection commands do not exist yet** (paused Slice A). Selection
  is an aggregate, not a state-target row, so the descriptor enum
  needs either a `selection` target or a decision to fold it
  elsewhere — section 6, question 4.

## 3. The two step-4 debts, resolved concretely

**(a) `reduceViewPose`'s command switch (pose math imports
`ViewCommand`).** The switch in `src/pose/viewPose.ts` is thin; the
real math lives in its private per-motion helpers (`orbitViewPose`,
`panViewPose`, `zoomViewPose`, `focusViewPose`, `restoreViewPose`).
Resolution: export those five with plain math params (deltas, factor,
center/zoom/orientation, pose snapshot) as the pose contract; move the
`ViewCommand -> motion params` switch up into interaction (the view
kind's descriptor `run`, or `authority`/`viewLane` where the coalesced
view is applied). `FocusViewOrientation` / `FocusViewTarget` are pose
vocabulary, not command vocabulary: move them into `src/pose` and have
`editor/commands.ts` import them downward (editor -> pose is already
the lawful direction). After this, `src/pose` imports nothing from
`editor/`, and the debt is gone rather than rehomed.

**(b) `framing.ts` consumes view policy.** `src/interaction/framing.ts`
composes `createGridFrameTarget` / `createGridViewportFocus` /
`createViewportFocusSelection` over scene + selection, and the core
already consumes the result only through `FramingPort`
(`framingState.port()` in `interactionCore.ts`, injected from App).
Resolution: keep `FramingPort` (+ `computeGridFrame` /
`computeSelectionFrame` signatures) in interaction as the port TYPE;
move the view-policy-consuming implementation out to the composition
side (App or a `src/view` framing module) and inject it. Interaction
then imports domain + pose only — MODEL.v2's layering sentence becomes
literally true and oxlint-checkable.

## 4. Slice A disposition: fold in, as the registry's first natives

Recommendation: **do not land Slice A on the old shape.** Its spec
adds two cases to `runSynchronous` — the exact switch step 4
dissolves. Sequence instead: land the registry spine first, then land
Slice A's `select` / `select-toggle` as the first commands registered
natively through descriptors (target `selection`, synchronous lane,
`repeat: none`, no `canRun`, `run` calling the same store actions the
spec names). This avoids touching the same code twice AND makes Slice
A the proof of the plugin seam: two brand-new commands added without
editing any switch. The spec's vocabulary, adapter conversions, and
deliberate boundaries (select-similar adapter-resolved, `addNeighbor*`
deferred) carry over unchanged; only the handler-wiring section
changes.

## 5. Interaction core contract

Mostly already clean, two gaps:

- `src/interaction/index.ts` exists and covers exactly the headless
  modules (`authority`, `bus`, `command`, `framing`,
  `interactionCore`, `morph`, `snapshot`, `viewLane`) — the camera
  driver/gesture/trackball adapter files are correctly NOT in it. But
  it is `export *` (the domain/evaluation/pose barrels are explicit
  re-exports) and has no oxlint guard, so deep imports and surface
  drift are unchecked. Curate it and add the guard pair; cheap,
  mechanical.
- The registry's new home: kind descriptors belong in the interaction
  core (they define lane/arbitration — bus concepts); affordance
  bindings (id/label/presets) stay editor-side with keymap and keypad.
  `bus`, `authority`, `snapshot` themselves need no reshaping; their
  contracts are already port-shaped and test-covered.

Adapter files moving out of `src/interaction/` is step 5, not step 4.

## 6. Open design questions for Stuart

1. **Registry keying.** Kind descriptors + separate affordance
   bindings (recommended, section 1), or one flat id-keyed list where
   kind facts repeat per binding? The flat list is simpler but
   recreates the reverse value-matching problem.
2. **`canRun` shape.** `true | { reason }` (recommended — the truthful
   synchronous lane already answers with reasons) vs bare boolean with
   a generic reason? And should `canRun` be evaluated for AFFORDANCE
   state too (keypad disabled-state reads), which is the VS Code
   `when`-clause / Blender `poll()` dual use?
3. **Lane answer unification.** Today `SynchronousDispatch`
   (`applied`/`rejected`+reason) and `ViewDispatch` (`accepted`+id)
   are different shapes, honestly reflecting different semantics. Keep
   two shapes (recommended) or unify into one result type with a
   status union? MODEL.v2 flags "how far to unify" as open.
4. **Selection's descriptor target.** Give the enum a `selection`
   value (aggregate-aligned, recommended) or classify selection
   commands under Mode? Ties to MODEL.v2's open "Selection undoability:
   session stance" lean.
5. **Transport promotion timing.** Promote play/pause/scrub/loop into
   the vocabulary during step 4 (completes the actor-facing taxonomy;
   BottomDock becomes an adapter) or defer to its own slice after? The
   descriptor row is otherwise empty.
6. **Growth-spine sequencing.** MODEL.v2 says rank the registry
   against `ShapeUtil` (part types) and the tool FSM. Registry first
   is implicit in this step's existence — confirm ShapeUtil/tool-FSM
   stay behind it, or does product pressure reorder?
7. **Descriptor placement for the plugin seam.** Central
   `commandDescriptors.ts` table (simplest now) vs per-context
   registration (`document.commands.ts`, `view.commands.ts` … calling
   `registerCommand`, the true plugin seam)? Central is fine for nine
   kinds; the registration API is what tldraw/VS Code converge on.

## 7. Risk and slicing (307 tests green at every step)

The command path is live; every slice is behavior-preserving until
Slice I4. Acceptance test throughout: full suite + lint green, and the
step-4 demo acceptance is "adding a command touches one descriptor and
zero switches" (proven by Slice A).

1. **I0 — curate the interaction barrel** (explicit re-exports +
   oxlint guard). Mechanical, unblocks the rest.
2. **I1 — kind descriptor table, facts only.** Introduce descriptors
   carrying `lane`/`arbitration`/`repeat`; reimplement
   `classifyCommand` and `getEditorCommandRepeatBehavior` as lookups
   (signatures preserved, call sites untouched); DELETE the reverse
   chain (`getEditorCommandId` + four helper matchers, ~150 lines) once
   repeat no longer needs it. Pinned by `interaction.command`,
   `commandHold`, keypad tests.
3. **I2 — `canRun` + `run` migration.** Descriptors gain handlers
   behind ports; `runSynchronous` becomes a generic executor (lookup,
   `canRun`, `run`); `dispatchCoreCommand`'s focus-toggle/reset
   enrichment becomes the view/focus descriptors' `run` with the
   framing port. The capture-toggle precondition becomes the first
   declared `canRun`.
4. **I3 — debts.** (a) pose motion functions exported, `ViewCommand`
   switch up into interaction, `FocusView*` types down into pose;
   (b) framing implementation out to composition, port stays. Both
   verifiable by "src/pose and src/interaction import from editor/
   view only where the design says" oxlint assertions.
5. **I4 — Slice A as first natives.** `select`/`select-toggle` per the
   existing spec, registered not switch-cased. Proves the seam.
6. **I5 (optional, Stuart's call per Q5) — transport commands.**
   `transport-play`/`pause`/`scrub`/`loop`; BottomDock converts to an
   adapter.

Steps I1/I2 stay inside `editor/` + `interaction/` + `app/`; the risky
surface is `useEditorCommands`/`useSynchronousEditorCommands` rewiring
in I2, which the injected-port test pattern from the interaction slice
already covers.
