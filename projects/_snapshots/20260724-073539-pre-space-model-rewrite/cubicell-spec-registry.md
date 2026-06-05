# Spec: command descriptor registry (MODEL.v2 step 4, slices I1-I5)

Design spec, 2026-07-10, by cubicell:general:8:6.1. Pins the contract
the build slices implement. Basis: main at 06ba766 plus grok's I0
(curated interaction barrel) landing separately. Companion scout:
`~/.mdx/projects/cubicell-scout-interaction.md`. Decisions below are
locked from the design round; do not relitigate.

Locked: per-context registration (`registerCommand`), not a central
table; two-level model (kind descriptors vs affordance bindings);
`canRun: true | { reason }`; the two lane-answer shapes stay distinct;
repeat is a kind-level fact (the ~150-line reverse chain in
`src/editor/commandRegistry.ts` is deleted); `selection` is a
descriptor target; transport commands are in scope (I5).

## 1. Types and registration API

New module: **`src/interaction/commands/registry.ts`** (interaction
core owns the registry; the name avoids colliding with
`src/editor/commandRegistry.ts`, which I1 slims and renames to
`src/editor/affordances.ts`).

```ts
import type { EditorCommand } from '../../editor/commands'
import type { SynchronousDispatch } from '../bus'
import type {
  CubicellScene, CubeSelection, CubeSelectionSet, SceneOperation,
} from '../../domain'

export type CommandTarget =
  | 'document' | 'view' | 'transport' | 'mode' | 'selection' | 'capture'
export type CommandLane = 'synchronous' | 'view'
export type CommandArbitration = 'additive' | 'absolute'
export type CommandRepeat = 'none' | 'discrete' | 'hold'
export type CanRunResult = true | { reason: string }

/** Read state a handler may consult. Composed by the executor per dispatch. */
export type CommandContext = {
  scene: CubicellScene
  selection: CubeSelection | null
  selectionSet: CubeSelectionSet | null
}

/** Write capabilities, grouped by context. Injected, never imported. */
export type CommandPorts = {
  capture: { toggle: (() => void) | null }
  document: {
    redo: () => void
    undo: () => void
    updateScene: (recipe: (scene: CubicellScene) => CubicellScene) => void
  }
  mode: {
    cyclePickMode: () => void
    setPickMode: (mode: CubeSelectionKind) => void
    toggleBuildMode: () => void
    toggleEditorMode: () => void
  }
  selection: {   // consumed from I4
    setSelection: (selection: CubeSelection | null) => void
    setSelectionSet: (set: CubeSelectionSet | null) => void
    toggleSelection: (selections: CubeSelection[]) => void
  }
  transport: {   // consumed from I5
    setTransportLoop: (loop: boolean) => void
    setTransportPlaying: (playing: boolean) => void
    setTransportTime: (timeMs: number) => void
  }
}

/** Core-side context for pre-dispatch resolution (focus-toggle, reset). */
export type CommandResolveContext = {
  authority: CameraAuthority
  framing: FramingPort
  initialCamera: CameraState
  viewportSize: ViewportSize
}

export type CommandKindDescriptor<K extends EditorCommand['kind'] = EditorCommand['kind']> = {
  kind: K
  target: CommandTarget
  lane: CommandLane                    // declared, not derived: the escape hatch is explicit
  arbitration?: CommandArbitration
    | ((command: Extract<EditorCommand, { kind: K }>) => CommandArbitration)
                                       // required iff lane === 'view'
  reversible: boolean                  // history: target 'document' + reversible false
  repeat: CommandRepeat
    | ((command: Extract<EditorCommand, { kind: K }>) => CommandRepeat)
  canRun?: (
    command: Extract<EditorCommand, { kind: K }>,
    ctx: CommandContext,
    ports: CommandPorts,
  ) => CanRunResult
  run?: (                              // synchronous lane only; view lane rides the bus
    command: Extract<EditorCommand, { kind: K }>,
    ctx: CommandContext,
    ports: CommandPorts,
  ) => SynchronousDispatch
  resolve?: (                          // optional core pre-dispatch enrichment
    command: Extract<EditorCommand, { kind: K }>,
    core: CommandResolveContext,
  ) => EditorCommand | { reason: string; status: 'rejected' }
}
```

Registration and lookup:

```ts
export type CommandRegistry = {
  classify: (command: EditorCommand) => CommandClass        // same shape as today's classifyCommand
  get: (kind: EditorCommand['kind']) => CommandKindDescriptor
  register: (descriptor: CommandKindDescriptor) => void      // throws on duplicate kind
  repeatBehavior: (command: EditorCommand) => CommandRepeat
}

export function createCommandRegistry(): CommandRegistry     // for tests / isolation
export const commandRegistry: CommandRegistry                // the default instance
export const registerCommand: CommandRegistry['register']    // bound to the default instance
```

Rules: `register` throws on duplicate `kind` and on `lane: 'view'`
without `arbitration`; `get` throws on unknown kind (mirrors today's
`getEditorCommandDefinition` throw). Facade functions preserve
existing call-site signatures: `classifyCommand` (today
`src/interaction/command.ts`) and `getEditorCommandRepeatBehavior`
(today `src/editor/commandRegistry.ts`) become thin delegates to
`commandRegistry.classify` / `.repeatBehavior` so I1 touches no
call sites.

## 2. Per-context file layout

```
src/interaction/commands/
  registry.ts            // types + createCommandRegistry + default instance (section 1)
  document.commands.ts   // registers: scene, history
  view.commands.ts       // registers: view, focus-toggle
  mode.commands.ts       // registers: editor-mode-toggle, build-mode-toggle, pick-mode, pick-mode-cycle
  capture.commands.ts    // registers: capture-toggle
  selection.commands.ts  // I4: select, select-toggle
  transport.commands.ts  // I5: transport-play, transport-pause, transport-scrub, transport-loop-toggle
  index.ts               // export function registerAllCommands(registry = commandRegistry): void
```

Each `*.commands.ts` exports one `register<Context>Commands(registry)`
function containing plain `registry.register({...})` calls; no
import-time side effects (explicit registration keeps tests and
tree-shaking honest). `registerAllCommands()` calls all of them once
and freezes the instance; it is invoked from the app composition root
(`src/app/App.tsx` module scope or `useEditorCommands` setup) and from
test setup. This is the plugin seam: a future part type or panel adds
a `*.commands.ts` and one line in `index.ts`, touching no switch.

Affordance bindings stay editor-side, untouched in role:
`src/editor/affordances.ts` (renamed from `commandRegistry.ts`) keeps
`editorCommandIds`, the 26 `{ id, label, command }` bindings (the
`scope` and `repeatable` fields are DELETED — both facts now live on
kind descriptors), and `getEditorCommandDefinition` for its two
consumers, `src/controls/view/viewControlDefinitions.ts` and
`src/editor/keyboard/keymap.ts`. Affordances reference kinds only
through the prebuilt `command` values they already carry.

## 3. Taxonomy mapping (the nine kinds + I4/I5 additions)

| Kind | target | lane | arbitration | reversible | repeat | canRun | run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `view` | view | view | fn: `focus`/`reset`/`restore` -> absolute, else additive (today's `isAbsoluteViewCommand`) | no | fn: `orbit` -> discrete; `pan`/`zoom` -> hold; `focus`/`reset`/`restore` -> none | — | — (bus -> authority) |
| `focus-toggle` | view | **synchronous** | — | no | none | — | — (has `resolve`, section 4) |

(Amended after I2 review: `focus-toggle` declares `lane: 'synchronous'`
— NOT view/absolute as this table first said — because main's
`classifyCommand` returned synchronous for it (only `kind: 'view'` was
view-lane) and parity is the I1/I2 gate. Its runtime routing still
ends on the view lane: `resolve` rewrites it to a `view` command
before the bus classifies. The `lane` fact describes the command as
dispatched, not as resolved.)
| `scene` | document | synchronous | — | yes | none | — | `ports.document.updateScene(applySceneOperation(...))` |
| `history` | document | synchronous | — | **false** (the escape hatch: targets Document via the History mechanism but is not itself undoable) | discrete | — | `undo`/`redo` by `command.direction` |
| `editor-mode-toggle` | mode | synchronous | — | no | none | — | `ports.mode.toggleEditorMode()` |
| `build-mode-toggle` | mode | synchronous | — | no | none | — | `ports.mode.toggleBuildMode()` |
| `pick-mode` | mode | synchronous | — | no | none | — | `ports.mode.setPickMode(command.mode)` |
| `pick-mode-cycle` | mode | synchronous | — | no | none | — | `ports.mode.cyclePickMode()` |
| `capture-toggle` | capture | synchronous | — | no | none | `ports.capture.toggle ? true : { reason: 'No capture surface' }` | `ports.capture.toggle!()` |
| `select` (I4) | selection | synchronous | — | no (session stance) | none | — | `setSelection` + optional `setSelectionSet`, per the Slice A spec |
| `select-toggle` (I4) | selection | synchronous | — | no | none | — | `toggleSelection(command.selections)` |
| `transport-play` (I5) | transport | synchronous | — | no | none | — | `setTransportPlaying(true)` |
| `transport-pause` (I5) | transport | synchronous | — | no | none | — | `setTransportPlaying(false)` |
| `transport-scrub` (I5) | transport | synchronous | — | no | none | — | `timeMs: number \| null`; null detaches the playhead (store Stop semantics), a number clamps to `[0, duration]` |
| `transport-loop-toggle` (I5) | transport | synchronous | — | no | none | — | `setTransportLoop(!ctx.transport.loop)` — current loop rides a read-only `ctx.transport` extension, keeping ports write-only |

(Amended after I5 review: scrub gained `null` for detach, and
loop-toggle reads current state from `ctx.transport.loop` rather than
a toggle port. Known follow-up: the scrub handler clamps via
`getScoreDurationMs`, giving `src/interaction` an evaluation import
that the I3 layering assertion did not list; either move the duration
into `ctx.transport.durationMs` (computed in the app hook, consistent
with the loop pattern) or amend MODEL.v2's "domain and pose math only"
sentence to admit pure Evaluation.)

Notes. `scene` repeat is `none` today by fact (no scene binding is
repeatable); if a repeatable scene op appears later it becomes the fn
form. `transport-scrub` carries `{ kind: 'transport-scrub', timeMs:
number }` — serializable, no object identity (INTERACTIVE.md inv 4);
scrub *gestures* coalesce in the adapter, each dispatch is discrete.
MODEL.v2's "Transport dual-writes" caveat is out of scope here: these
commands write the playhead through the store; camera-track
contention already rides the authority via detach and is untouched.

## 4. Executor and core integration

**Synchronous executor** (replaces the switch in
`src/app/useSynchronousEditorCommands.ts` `runSynchronous`):

```ts
const runSynchronous: SynchronousPort = (command) => {
  const descriptor = commandRegistry.get(command.kind)
  if (descriptor.lane !== 'synchronous' || !descriptor.run) {
    return { reason: `Unhandled synchronous command: ${command.kind}`, status: 'rejected' }
  }
  const allowed = descriptor.canRun?.(command, ctx, ports) ?? true
  if (allowed !== true) {
    return { reason: allowed.reason, status: 'rejected' }
  }
  return descriptor.run(command, ctx, ports)
}
```

The hook builds `ctx` from its existing props (`scene`, `selection`,
`selectionSet`) and `ports` from the store actions it already selects;
`registerCapture` keeps feeding `ports.capture.toggle`. The truthful
fall-through rejection is preserved verbatim.

**Core dispatch** (replaces `dispatchCoreCommand`'s hardcoded cases in
`src/interaction/interactionCore.ts`): before routing, the core runs
`descriptor.resolve?.(command, coreCtx)`; a returned command is
dispatched in its place, a returned rejection is the dispatch answer.
`focus-toggle`'s `resolve` reproduces `dispatchFocusToggle` (restore
pose vs selection frame via `framing`, including the two rejection
reasons "No saved focus pose" / "No focusable selection");
`view`+`reset`'s `resolve` reproduces `dispatchReset` (clearFocus +
grid frame target). `resolve` is the only descriptor field with core
context; nothing else sees the authority.

**Lane answers stay two-shaped** (locked): `SynchronousDispatch`
(`applied` / `rejected` + reason) and `ViewDispatch` (`accepted` + id)
as defined in `src/interaction/bus.ts`, unchanged.

## 5. Slices I1-I5 against this contract

- **I1 — registry + facts.** Add `registry.ts` + the four existing
  context files registering facts only (no `canRun`/`run`/`resolve`
  yet); `classifyCommand` and `getEditorCommandRepeatBehavior` become
  delegates; DELETE `getEditorCommandId` + `getOrbitCommandId` /
  `getPanCommandId` / `getZoomCommandId` / `getPickModeCommandId` /
  `getSceneCommandId` + `getEditorCommandDefinitionForCommand`; rename
  `src/editor/commandRegistry.ts` -> `affordances.ts` dropping `scope`
  + `repeatable` from `EditorCommandDefinition`. Acceptance: full
  suite green with no call-site edits outside the renamed import; grep
  `getEditorCommandId` -> zero hits; `canRepeatViewCommand` in
  `commands.ts` deleted (its rule now lives in the `view` descriptor's
  repeat fn).
- **I2 — canRun/run/resolve.** Fill the table's handler columns for
  the nine kinds; swap `runSynchronous` to the executor and
  `dispatchCoreCommand` to resolve-then-route. Acceptance: suite green
  (`tests/interaction.core.test.ts` pins focus-toggle/reset behavior
  and the capture rejection); the switch bodies are deleted, not
  bypassed.
- **I3 — the two debts.** See section 6. Acceptance: the import-
  direction assertions there, plus suite green.
- **I4 — Slice A natively.** `select` / `select-toggle` per the spec
  on branch `interaction/selection-commands`
  (`docs/superpowers/specs/2026-07-09-interaction-selection-commands-design.md`):
  vocabulary + constructors in `editor/commands.ts`,
  `selection.commands.ts` registers descriptors (table above), adapter
  conversions per that spec (`useSceneOperations`, `PartSection`,
  `StructureSection`). Acceptance: that spec's acceptance paragraph,
  PLUS the step-4 demo: the diff adds zero cases to any switch.
- **I5 — transport commands.** Extend the union + constructors with
  the four kinds; `transport.commands.ts` registers them;
  `src/panels/BottomDock.tsx` converts to dispatching (its
  `setTransportTime` / `setTransportPlaying` selectors replaced by
  `useEditorCommandDispatch`); `ports.transport` wired from existing
  store actions. `src/transport/TransportDriver.tsx` is NOT converted:
  it is the clock, not an actor (the time-source seam). Acceptance:
  BottomDock has no store-write selectors; an actor holding only
  `dispatch` can play, pause, scrub, and toggle loop;
  `tests/state.test.ts` transport behavior unchanged.

## 6. Debt resolutions (I3) as import-direction assertions

**(a) pose math / command vocabulary.**
Before: `src/pose/viewPose.ts` imports `ViewCommand`,
`FocusViewOrientation` from `../editor/commands`; `reduceViewPose`
switches on `ViewCommand` inside pose math.
Change: export the per-motion functions from pose with plain params —
`orbitViewPose(pose, thetaDelta, phiDelta, initial)`,
`panViewPose(pose, xDelta, yDelta, initial)`, `zoomViewPose(pose,
factor)`, `focusViewPose(pose, center, zoom, orientation, initial)`,
`restoreViewPose(pose, snapshot)` (today's private helpers, promoted
to the pose barrel); MOVE `FocusViewOrientation` + `FocusViewTarget`
into `src/pose` (they are pose vocabulary) and re-export from
`editor/commands.ts` for compatibility; MOVE the `ViewCommand ->
motion` switch to a new `src/interaction/viewReducer.ts` (the view
lane's interpreter), re-pointing `cameraAuthorityRuntime.ts` and
`orbitDetent.ts`.
After-assertions: `grep -rn "editor/" src/pose/` -> zero hits;
`editor/commands.ts` imports `FocusViewOrientation` from `'../pose'`;
`reduceViewPose` no longer exists in `src/pose`.

**(b) framing / view policy.**
Before: `src/interaction/framing.ts` imports
`createViewportFocusSelection`, `hasSelectionTarget`,
`createGridFrameTarget`, `createGridViewportFocus` from `'../view'`.
Change: keep `FramingPort`, `ViewportSize`, and the
`computeGridFrame` / `computeSelectionFrame` SIGNATURES in
`src/interaction/framing.ts`; move their view-policy-consuming
implementations to `src/view/interactionFraming.ts` (view -> pose ->
domain, all lawful) and inject them through the existing `framing`
argument of `createInteractionCore` (`src/app/App.tsx` /
`useEditorCommands` already construct the port).
After-assertions: `grep -rn "from '../view'" src/interaction/` -> zero
hits; `src/interaction` imports only `domain`, `pose`, `editor`
(command types), internal modules; the oxlint guard for view stays
satisfied barrel-to-barrel from `src/view/interactionFraming.ts`'s
consumers.

## 7. Cross-slice interfaces

- I1 exports `CommandRegistry` / `CommandKindDescriptor` /
  `registerCommand` / `registerAllCommands`; I2-I5 consume them.
- I2 pins `CommandContext` / `CommandPorts` / `CommandResolveContext`;
  I4 consumes `ports.selection`, I5 consumes `ports.transport` (both
  groups declared in I2's `CommandPorts` from the start, wired when
  their slice lands; unwired groups hold no-op throwing stubs so a
  premature dispatch fails loudly).
- I3's pose motion functions are consumed by I3's own
  `viewReducer.ts` only; no other slice depends on I3, so it can land
  any time after I1 (I4/I5 do not block on it).
- Every slice keeps the 307-test suite green; new behavior arrives
  with its own tests per the patterns in `tests/interaction.*.test.ts`
  (injected ports, no store in core tests).
