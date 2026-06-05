# Cubicell Agent Observability: Snapshot / Act / Observe

Status: DRAFT v2.3 for final sign-off (2026-07-10)
Author: orchestrator (Fable), from Stuart's brief + cm decision 019f4b7b (parked trace MVP, now unparked into spec)
v2: synthesis of four-family panel review (fable, opus, grok, gpt), all conditionals applied. Baseline: fix/gap0-coplanar-face-fighting @ 10fd6a1 (448 tests green).
v2.2: final-round deltas — gesture.mirror dropped from span vocabulary (fable); ActionEnvelope / SpanTraceEvent / SerializedDispatchResult defined, coalesced settle carries commandId→correlationId pairs, anchor typed SceneSnapshot with before-earliest-event semantics (gpt).

## 1. Problem

Cubicell emits no trace output. Debugging per-frame interaction bugs (the PERSP→ORTHO morph jitter) required hand-rolling temporary per-frame instrumentation and stripping it afterward, twice. Separately, Stuart's product direction: an LLM agent should be able to (a) get a snapshot of the scene at a point in time, (b) trigger an action, and (c) review a payload of what happened.

## 2. Decisions already made (do not relitigate)

1. **Payload-first.** The snapshot/trace/action schemas are the contract. The offline path ships first (in-app dump to JSON, human hands the file to an LLM). A live agent bridge (MCP/WebSocket) bolts on later against the same schemas without rework. Confirmed by Stuart this session.
2. **Ring buffers, not per-frame console.** Bounded buffers holding the last ~2s of frames / N events. See the jank, then dump; the anomaly is already captured. Per-frame console.log floods, perturbs timing, and is uncorrelatable.
3. **Two chokepoints, not scattered trace calls.** (1) The **InteractionCore boundary**: one decorator over `createInteractionCore`'s returned surface (`dispatch`, `holds.begin/end`, `gesture.begin/mirror/end`) captures every discrete command with its `DispatchResult`, plus hold and gesture spans. Panel-verified: React-level wrappers (`dispatchEditorCommand`) miss real traffic (`cameraWheelZoom` calls `core.dispatch` directly; holds and gestures bypass dispatch entirely). (2) The **per-frame camera writer**: one hook in `useSingleCameraWriterFrame` gives the frame timeline. The trace module mints the monotonic frame id and dt (neither exists in the writer today).
4. **Dev-flag gated, no-op in prod.** A persisted preference in `CubicellPreferences`, runtime-togglable via `patchPreferences`, behind an `import.meta.env.DEV` static guard (pattern: `src/main.tsx`) so prod builds tree-shake the recorder to a no-op.
5. **Scope discipline.** MVP = two ring buffers + core decorator + frame hook + snapshot provider + dump keybind + dev flag. NOT a telemetry pipeline, no network transport, no analytics, no perf profiler.

## 3. Capabilities

Three capabilities, one shared vocabulary. The unit of exchange is a versioned, serializable JSON payload.

### 3.1 Snapshot (read model)

`captureSnapshot(sections?)` returns the scene at a point in time.

**v1 ships summary-only** (panel consensus); `sections?` stays in the schema as the tiering contract so drill-down is a fast follow, not a rework. The summary is **built on the existing read model**: `composeSnapshot` / `InteractionSnapshot` / `toPoseSnapshot` from `src/interaction/snapshot.ts`, surfaced today as `core.getState()` (pose tuples, projection, poseMode, morphing, selection; already consumed by the frame writer and covered by `tests/interaction.snapshot.test.ts`). No parallel pose or selection serializer. The future `sections.document` reuses `CubicellDocument` (grid, polarity, projection, score included), not an invented objects list.

### 3.2 Act (command surface)

No new execution path. Every actor already speaks the same serializable `EditorCommand` payload (MODEL.v2 one-payload thesis, proven by select-query). The spec adds an **ActionEnvelope**: a `correlationId` minted at dispatch and carried through the view-lane queue, so the frame-drain apply is attributable to its dispatch. Holds and gestures reuse their **native span ids** (`holdId` minted by `bus.beginHold`; a span id minted at `gesture.begin`); no new span machinery. In the offline MVP, "act" is the human driving the app; the agent reviews afterward. The live bridge later exposes `act(command) -> ActionRecord` over the same envelope.

### 3.3 Observe (trace)

Two bounded ring buffers sharing one monotonic `seq`: a **frame ring** (`camera.frame`, ~120 events per 2s) and a **discrete ring** (command/hold/gesture lifecycle), merged by `seq` on dump so frame flood can never evict command history (unanimous panel finding). Dump targets: downloadable JSON file (the payoff: hand a trace to an LLM); console table and dev overlay are non-MVP. An `ActionRecord` is derived on demand, never stored: the trace slice for one `correlationId`, closed at settle for view-lane commands.

## 4. Schemas (the contract)

All payloads carry `v` (schema version, start at 1). Projection vocabulary is the domain's `ProjectionMode` (`'perspective' | 'orthographic'` from `src/domain/scene.ts`); no forked strings.

```ts
type TraceEvent =
  | CommandTraceEvent   // type: 'command.dispatched' | 'command.accepted' | 'command.applied'
                        //     | 'command.rejected' | 'command.settled'
  | SpanTraceEvent      // type: 'hold.begin' | 'hold.end' | 'gesture.begin' | 'gesture.end'
                        // (no gesture.mirror: it fires at pointer-move rate and would flood the
                        //  discrete ring; per-frame pose is already on camera.frame)
  | FrameTraceEvent;    // type: 'camera.frame'

type TraceEventBase = {
  v: 1;
  seq: number;          // monotonic across BOTH rings; ordering + eviction visibility
  t: number;            // performance.now() ms
  frame: number;        // monotonic frame id minted by the trace module
  category: 'command' | 'camera';   // enum reserves 'morph' | 'gesture' | 'selection';
                                    // MVP emits only these two (morph rides camera.frame,
                                    // spans are category 'command')
  correlationId?: string;
};

type ActionEnvelope = {
  correlationId: string;  // minted at dispatch, carried through the view-lane queue
  dispatchedAt: number;   // t at dispatch; settle latency = settle.t - dispatchedAt
};

type SerializedDispatchResult =           // mirrors DispatchResult (src/interaction/bus.ts)
  | { lane: 'synchronous'; status: 'applied' | 'rejected'; reason?: string }
  | { lane: 'view'; status: 'accepted'; commandId: number };  // number per ViewDispatch (bus.ts)

type CommandTraceEvent = TraceEventBase & {
  type: `command.${'dispatched' | 'accepted' | 'applied' | 'rejected' | 'settled'}`;
  payload: {
    command?: EditorCommand;        // dispatched
    result?: SerializedDispatchResult;
    coalesced?: Array<{ commandId: number; correlationId: string }>;
                                    // settled: every command drained together in resolveFrame,
                                    // each mapped back to its envelope unambiguously
    disposition?: 'settled' | 'interrupted';
  };
};

type SpanTraceEvent = TraceEventBase & {
  type: 'hold.begin' | 'hold.end' | 'gesture.begin' | 'gesture.end';
  correlationId: string;            // required: native holdId, or span id minted at gesture.begin
  payload: { kind: 'hold' | 'gesture'; source?: string };
};

type FrameTraceEvent = TraceEventBase & {
  type: 'camera.frame';
  payload: {
    dt: number;
    projection: ProjectionMode;     // ortho-aware: fov for perspective,
    fov?: number;                   // halfWidth/zoom for orthographic
    orthoHalfWidth?: number;
    zoom?: number;
    near: number; far: number;
    pose: PoseSnapshot;             // reuse from src/interaction/snapshot.ts
    poseMode: string;
    morph?: { orthoBlend: number }; // ProjectionMorphSample passthrough
  };
};

type SceneSnapshot = {
  v: 1;
  t: number;
  frame: number;
  summary: InteractionSnapshot & {  // reuse: pose, projection, poseMode, morphing, selection
    counts: Record<string, number>; // entity counts from the document
    mode: string;
  };
  sections?: { document?: CubicellDocument; prefs?: Partial<CubicellPreferences> }; // post-v1
};

type ActionRecord = {              // derived on demand, never stored
  v: 1;
  correlationId: string;
  command: EditorCommand;
  outcome: 'applied' | 'rejected' | 'accepted';  // matches DispatchResult
  settled?: { frame: number; disposition: 'settled' | 'interrupted' };
  before: SceneSnapshot['summary'];
  after: SceneSnapshot['summary'];
  events: TraceEvent[];
};

type TraceDump = {
  v: 1;
  sessionId: string;
  capturedAt: string;              // ISO
  timeOrigin: number;
  window: { start: number; end: number };   // t-range of retained events
  reason: 'keybind' | 'api';
  env: { viewport: [number, number]; dpr: number; reducedMotion: boolean;
         feel?: Record<string, number> };
  snapshot: SceneSnapshot;         // at dump time
  anchor?: SceneSnapshot;          // state BEFORE the earliest retained event; v1 may
                                   // omit it until that checkpoint can be maintained
                                   // (populating at trace-enable is a valid v1 approximation
                                   // only while no eviction has occurred)
  dropped: { frames: number; discrete: number };  // eviction counts since enable
  events: TraceEvent[];            // both rings merged by seq
};
```

## 5. Reuse map (path + symbol; panel-verified against fix/gap0-coplanar-face-fighting)

- **Command chokepoint**: `createInteractionCore` / `dispatchCoreCommand` in `src/interaction/interactionCore.ts`; its `dispatch` returns `DispatchResult` (`src/interaction/bus.ts`) synchronously, including view-lane `{commandId, status: 'accepted'}`. View commands drain and apply in `resolveFrame` (coalesced); the settle emit lives there. Holds: `bus.beginHold`/`endHold` (native `holdId`). Gestures: `core.gesture.begin/mirror/end` (called from `src/camera/cameraGestureRuntime.ts`).
- **Command payloads/taxonomy**: `EditorCommand` in `src/editor/commands.ts`; registry `commandRegistry`/`CommandKindDescriptor` in `src/interaction/commands/registry.ts`; `editorCommandDefinitions` in `src/editor/affordances.ts`.
- **Frame chokepoint**: `useSingleCameraWriterFrame` in `src/camera/cameraFrameWriter.ts` composing via `composeCameraWrite` in `src/camera/cameraDriverMath.ts`. Morph state is owned by `CameraAuthorityState.morph` (`src/camera/cameraAuthorityRuntime.ts`) and `src/interaction/morph.ts`; the writer already receives `ProjectionMorphSample` (`orthoBlend`), so no third tap. `src/camera/cameraProjectionSwap.ts` only triggers `beginMorph`.
- **Snapshot read model**: `composeSnapshot` / `InteractionSnapshot` / `toPoseSnapshot` / `SelectionSnapshot` in `src/interaction/snapshot.ts` via `core.getState()`. Selection summary uses `SelectionSnapshot`; no retained query string exists in state, so no `query` field.
- **Dev flag**: new field on `CubicellPreferences` (`src/state/cubicellState.ts`) toggled via `patchPreferences` (`src/state/cubicellStore.ts`, persisted through the existing `debouncedJsonStorage` adapter); recorder construction guarded by `import.meta.env.DEV`.
- **Dump plumbing**: keybind through `src/editor/keyboard/keymap.ts` / `KeyboardShortcuts`; JSON download by extracting a generic blob-download helper from `downloadRecording` / `createRecordingStamp` in `src/export/canvasRecorder.ts` so both callers share it.
- **Deviation: none.** New code lives in one module: `src/trace/` (rings, event types, snapshot provider, dump, core decorator). Taps are the decorator plus one frame-writer call.

Out of scope (panel-corrected): the `console.warn` in `src/state/debouncedJsonStorage.ts` stays; it is intentional persistence-failure visibility, not debug cruft. The trace may additionally observe such failures later; it does not replace them.

## 6. Non-goals

Telemetry pipeline, network transport, prod analytics, performance profiling, replay engine (the format must not preclude replay; `seq`, `anchor`, `env`, and typed payloads exist for that reason), live MCP bridge (phase 2, same schemas), console table / dev overlay, snapshot sections beyond the schema contract.

## 7. Resolved questions (was: open questions)

1. **Tiering**: summary-only in v1; `sections?` stays in the schema as the contract (3 of 4 reviewers; GPT's document-section content folded into the contract as `CubicellDocument`).
2. **Correlation**: `correlationId` at dispatch, carried through the view queue to a `command.settled` emit in `resolveFrame` (captures dispatch→apply latency, the morph-jitter signal). Holds/gestures reuse native span ids. No new span machinery.
3. **Rings**: two rings, shared monotonic `seq`, merged on dump. Frame flood cannot evict command history.
4. **Dev flag**: persisted `CubicellPreferences` field + `import.meta.env.DEV` compile guard.
5. **Bridge/replay blockers**: resolved via three-valued outcome + settle events, typed payloads, ortho-aware frame payload, `sessionId`/`seq`/`timeOrigin`/`window`/`anchor`/`env`/`dropped` on the dump.

## 8. Verification gate

Unit tests for ring eviction (incl. `dropped` counts and cross-ring `seq` merge), correlation slicing incl. view-lane settle, and snapshot shape (vitest, existing `tests/` conventions). Integration tests through the real core: (a) dispatch a synchronous command with tracing on, assert dispatched/applied events share the `correlationId`; (b) dispatch a view command, assert accepted→settled with coalesced ids; (c) a hold begin/end pair appears with its `holdId`. `pnpm test` green (baseline 448 tests at 10fd6a1).
