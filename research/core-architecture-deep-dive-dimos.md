---
title: "DimOS Core Architecture Deep Dive"
type: research
tags: [architecture, robotics, module-system, reactive-streams, agents, dimos]
summary: "Complete architectural analysis of DimOS core, agent, stream, and skill systems with relevance assessment for non-robotics applications"
status: active
source: codebase-analyst
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

DimOS is an open-source robotics framework (Apache 2.0, by Dimensional Inc.) built around a **module-blueprint-transport** architecture. Modules are isolated units of computation that communicate through typed reactive streams, orchestrated by a blueprint system that handles dependency injection, stream wiring, and RPC binding. The framework runs modules in separate worker processes, connected via multiprocessing pipes, and uses LCM (Lightweight Communications and Marshalling) as the default transport. The agent system wraps LangChain/LangGraph for LLM-powered control, with skills exposed as RPC-callable tools.

The codebase is 860 files, 138K LOC of Python, with a `dimos/agents_deprecated/` directory (5,362 LOC) indicating a recent agent system rewrite.

## Project Metadata

| Field | Value |
|-------|-------|
| Language | Python 3.10+ |
| Build system | setuptools + pybind11 |
| Version | 0.0.11 |
| License | Apache 2.0 |
| Total LOC | ~138,634 (860 files) |
| Key deps | RxPY, LCM, LangChain/LangGraph, OpenCV, pydantic, FastAPI |
| Author | Dimensional Inc. |

## Architecture

### The Four Pillars

DimOS is structured around four interlocking concepts:

1. **Module** -- the unit of computation
2. **Stream (In/Out)** -- typed reactive data ports on modules
3. **Transport** -- the wire protocol connecting streams across processes
4. **Blueprint** -- the composition and wiring layer

### 1. Module System (`dimos/core/module.py`, 475 LOC)

The module hierarchy:

```
Resource (ABC)           -- start()/stop() lifecycle
  Configurable[T]        -- typed config via dataclass
    ModuleBase[T]        -- RPC, streams, TF, disposables, asyncio loop
      Module[T]          -- automatic In/Out instantiation from type annotations
        NativeModule     -- wraps a C/C++ subprocess
```

**Key design decisions:**

- **Declarative stream ports.** Modules declare `In[T]` and `Out[T]` as class-level type annotations. `Module.__init__` introspects these via `get_type_hints()` and instantiates the actual `In`/`Out` objects automatically.

```python
class SimpleRobot(Module[SimpleRobotConfig]):
    cmd_vel: In[Twist]        # auto-instantiated
    pose: Out[PoseStamped]    # auto-instantiated
```

- **RPC via decorator.** The `@rpc` decorator (in `dimos/core/core.py`, 3 lines) sets `fn.__rpc__ = True`. The system introspects for this marker to register methods for cross-process calling.

- **Multi-process isolation.** Each module runs inside a `Worker` process (forkserver context, to avoid CUDA issues). The parent holds `Actor` proxies that forward method calls through `multiprocessing.Pipe`. This is a custom implementation replacing what was previously Dask actors (comments in code reference "Dask's ActorFuture").

- **Lifecycle:** `__init__` -> blueprint wires transports -> `start()` -> `on_system_modules()` (agent-only) -> ... -> `stop()` -> `_close_module()`.

**File: `dimos/core/worker.py` (389 LOC)**

The worker system is a clean multiprocessing Actor model:
- `Worker` manages a subprocess via `forkserver` context
- `Actor` is the parent-side proxy, forwarding calls over a `Pipe`
- `MethodCallProxy` wraps Actor for `RemoteOut`/`RemoteIn` serialization
- `WorkerManager` (`dimos/core/worker_manager.py`, 117 LOC) distributes modules across N workers using round-robin

### 2. Stream System (`dimos/core/stream.py`, 269 LOC)

Streams are typed, directional, observable data channels:

```
Stream[T]              -- base: name, type, owner, optional transport
  Out[T]               -- publish(msg), subscribe(cb), serializes to RemoteOut
  In[T]                -- subscribe(cb), gets transport from connection
  RemoteStream[T]      -- base for cross-process stream references
    RemoteOut[T]       -- subscribes through transport
    RemoteIn[T]        -- connects through owner proxy
```

**State machine:** `UNBOUND -> READY -> CONNECTED -> FLOWING`

**ObservableMixin** provides RxPY integration:
- `observable()` -- returns a backpressured Observable
- `get_next(timeout)` -- blocks for one value
- `hot_latest()` -- returns a getter that always has the latest value
- `pure_observable()` -- raw Observable without backpressure

**Transport** is the abstract wire protocol:

```python
class Transport(Resource, ObservableMixin[T]):
    def broadcast(self, selfstream: Out[T], value: T) -> None: ...
    def subscribe(self, callback, selfstream) -> Callable[[], None]: ...
```

**Concrete transports** (`dimos/core/transport.py`, 323 LOC):
- `LCMTransport` -- uses LCM's native encode/decode
- `pLCMTransport` -- pickle over LCM (for types without `lcm_encode`)
- `SHMTransport` / `pSHMTransport` -- shared memory
- `JpegShmTransport` -- JPEG-compressed shared memory (for images)
- `ROSTransport` -- ROS bridge
- `ZenohTransport` -- stub

This is a well-designed transport abstraction. The type system determines whether to use native LCM encoding or pickle fallback, transparently.

### 3. Blueprint System (`dimos/core/blueprints.py`, 537 LOC)

The blueprint is an immutable, composable build plan. It uses a **builder pattern with frozen dataclasses**:

```python
# Usage pattern:
autoconnect(
    SimpleRobot.blueprint(),        # Module.blueprint is a classproperty
    NavigationSkillContainer.blueprint(),
).global_config(n_workers=4)
 .transports({("pose", PoseStamped): custom_transport})
 .remappings([(ModA, "old_name", "new_name")])
 .requirements(check_gpu_available)
 .build()
 .loop()
```

**`build()` sequence:**
1. Apply global config overrides
2. Run system configurators (LCM setup, etc.)
3. Check requirements
4. Verify no stream name/type conflicts
5. Deploy all modules in parallel (`ModuleCoordinator.deploy_parallel`)
6. Connect streams by matching name + type across modules
7. Wire RPC methods (by name convention and Spec matching)
8. Connect module references (Spec-based dependency injection)
9. Start all modules, call `on_system_modules()` on agents

**`autoconnect()`** merges multiple blueprints, deduplicating modules. Stream wiring is **name-based**: an `Out[Twist]` named `cmd_vel` automatically connects to any `In[Twist]` named `cmd_vel` across all modules in the blueprint.

**Spec system** (`dimos/spec/`, 348 LOC) enables interface-based dependency injection:

```python
class Image(Protocol):
    color_image: Out[ImageMsg]

class Camera(Image):
    camera_info: Out[CameraInfo]
```

Modules can declare a dependency on a Spec (Protocol), and the blueprint resolves it to a concrete module using structural + annotation compliance checking. This is Python's `Protocol` type used as a runtime service locator.

### 4. Agent System (`dimos/agents/`, 4,246 LOC)

The Agent is a Module that wraps LangChain/LangGraph:

```python
class Agent(Module[AgentConfig]):
    agent: Out[BaseMessage]        # emits all messages
    human_input: In[str]           # receives human text
    agent_idle: Out[bool]          # busy/idle status
```

**Agent lifecycle:**
1. `__init__`: queue, history, thread setup
2. `start()`: subscribes to `human_input` stream
3. `on_system_modules(modules)`: creates LangGraph state graph, discovers skills from all modules, starts processing thread
4. Thread loop: dequeues messages, streams through LangGraph, publishes responses

**Skill discovery** is automatic. When `on_system_modules` is called, the agent queries `get_skills()` on every module in the system. Any method decorated with `@skill` (from `dimos/agents/annotation.py`) is surfaced as a LangChain `StructuredTool`.

```python
# annotation.py -- 4 lines of actual code
def skill(func):
    func.__rpc__ = True    # makes it callable via RPC
    func.__skill__ = True  # makes it discoverable by agents
    return func
```

The `@skill` decorator is a superset of `@rpc`. Skills are called through RPC, meaning an agent in one process can invoke a skill running in a different worker process.

**MCP integration** (`dimos/agents/mcp/`, 1,281 LOC):
- `McpServer` -- FastAPI-based HTTP server exposing module RPCs as MCP tools
- `McpClient` -- client for connecting to external MCP servers
- `McpAdapter` -- bridges external MCP tools into the DimOS skill system

### Legacy Skills System (`dimos/skills/`, 2,061 LOC)

There are **two skill systems** in the codebase:

1. **New system** (in `dimos/agents/`): `@skill` decorator on Module methods, discovered via RPC introspection. Clean, compositional.

2. **Legacy system** (in `dimos/skills/`): `SkillLibrary` + `AbstractSkill` (Pydantic BaseModel subclasses), `AbstractRobotSkill`. Uses OpenAI function tool format. More verbose, robot-centric.

The new system is clearly the direction. The legacy system likely persists for manipulation skills that haven't been migrated.

### Stream Layer (`dimos/stream/`, 4,141 LOC)

Higher-level stream infrastructure built on the core stream primitives:

- **Video pipeline:** `VideoProvider` (OpenCV capture -> Observable), `FrameProcessor` (CV operations as rx operators), `VideoOperators` (resize, annotate, etc.)
- **Audio pipeline:** `AudioEvent` base type, emitter/consumer/transform ABCs, microphone capture, TTS (OpenAI/pyttsx3), STT (Whisper), volume monitoring, normalization
- **Stream utilities:** `StreamMerger` for combining typed observables

All use RxPY observables with `ThreadPoolScheduler` for concurrent processing.

### Type System (`dimos/types/`, 2,950 LOC)

- `Timestamped[T]` -- adds temporal metadata (287 LOC, 41 downstream dependents)
- `Vector` -- 3D vector with full math operations (457 LOC)
- `WeakList` -- weak-reference list for avoiding reference cycles
- `Sample` -- typed sample container
- `RobotLocation` -- GPS/pose location type
- `RobotCapabilities` -- capability flags
- `ros_polyfill` -- lightweight ROS message type shims

### Protocol Layer (`dimos/protocol/`, 9,194 LOC)

The protocol layer provides the actual communication implementations:

| Subpackage | LOC | Purpose |
|-----------|-----|---------|
| `pubsub/` | 4,741 | Pub/sub implementations (LCM, SHM, ROS, DDS) |
| `service/` | 2,152 | System configuration services |
| `tf/` | 1,138 | Transform frame management (like ROS tf2) |
| `rpc/` | 1,074 | RPC over LCM |
| `encode/` | 89 | Message encoding utilities |

The PubSub spec (`dimos/protocol/pubsub/spec.py`) defines:
- `PubSub` -- basic publish/subscribe
- `AllPubSub` -- subscribe to all topics
- `DiscoveryPubSub` -- topic discovery
- `PubSubBaseMixin` -- async iteration, queuing

## Key Patterns

### Pattern 1: Annotation-Driven Wiring

The most distinctive pattern. Module ports are declared as type annotations, not runtime registrations. The framework introspects these at multiple levels:
- `Module.__init__` creates stream instances
- `Blueprint` reads annotations to plan wiring
- `module_info` descriptor provides introspection from both class and instance level

### Pattern 2: Frozen Immutable Builders

Blueprint uses `@dataclass(frozen=True)` with `replace()` for immutable transformations. Each builder method returns a new Blueprint. This prevents accidental mutation during composition.

### Pattern 3: Actor Model Over Pipes

Custom multiprocessing actor system using `forkserver` context. Each worker is a long-running process with a message loop. Modules are deployed into workers and accessed through Actor proxies. This replaced Dask distributed actors for better control over lifecycle and CUDA compatibility.

### Pattern 4: Protocol-Based DI

Python `Protocol` types serve as service interfaces. The blueprint's `_connect_module_refs` performs runtime structural + annotation matching to wire modules that satisfy a spec. Disambiguation is explicit (via `.remappings()`).

### Pattern 5: Skill = RPC + Discovery

A `@skill` is just an `@rpc` with a `__skill__` flag. The agent discovers skills by iterating all system modules and calling `get_skills()`. Each skill becomes a LangChain tool. The entire bridge from module method to LLM-callable tool is ~50 lines.

## Detailed Findings

### How the Module Concept Works

`ModuleBase` inherits from both `Configurable[T]` (typed config) and `Resource` (start/stop lifecycle). `Module` adds automatic stream instantiation.

Key files:
- `dimos/core/module.py:84-387` -- `ModuleBase` (304 LOC)
- `dimos/core/module.py:390-465` -- `Module` (76 LOC)
- `dimos/core/stream.py:97-136` -- `Stream` base
- `dimos/core/stream.py:139-184` -- `Out`
- `dimos/core/stream.py:213-249` -- `In`

### NativeModule for FFI

`NativeModule` (`dimos/core/native_module.py`, 296 LOC) wraps C/C++ executables as blueprint-compatible modules. It:
1. Declares In/Out ports like any Module
2. On `start()`, collects LCM topic strings from blueprint-assigned transports
3. Passes topics as CLI args to the subprocess
4. The native process does pub/sub directly on LCM multicast

This is a clean FFI boundary: Python handles orchestration, native code handles computation.

### Agent RPC Method Resolution

Agents request RPC methods by name (e.g., `"NavigationInterface.set_goal"`). The blueprint builds a method registry from all module RPCs, indexing by both concrete class name and abstract interface name. When a module declares:

```python
rpc_calls: list[str] = [
    "SpatialMemory.tag_location",
    "NavigationInterface.set_goal",
]
```

The blueprint wires these to actual module proxies at build time (`_connect_rpc_methods`, line 396-472).

### Worker Distribution

`WorkerManager` creates N workers (default 2) and distributes modules round-robin. Modules within the same worker share a process. Cross-module communication goes through transports (LCM multicast), not through the parent pipes.

## Relevance to Non-Robotics Applications

### Directly Reusable Abstractions

1. **Module + Blueprint + autoconnect**: The composition pattern is domain-agnostic. Any system with typed data flowing between processing nodes could use this. Indoor mapping, data pipelines, sensor fusion.

2. **Stream In/Out with Transport abstraction**: The separation of stream ports from transport protocol is clean. You could swap LCM for WebSocket, MQTT, or in-memory queues.

3. **Spec-based dependency injection**: Protocol-based DI with structural matching is usable anywhere you need pluggable components.

4. **NativeModule pattern**: Wrapping native executables with declarative stream ports and CLI topic passing is applicable to any system integrating native computation.

5. **@skill -> LLM tool bridge**: The pattern of decorating methods to make them LLM-callable with automatic schema extraction is portable.

### What Would Need Changing for Indoor Mapping

- **Transport layer**: LCM is robotics-specific. For a web app, you'd want WebSocket or HTTP/SSE transports. The abstraction supports this cleanly.
- **Worker model**: The forkserver process model assumes a single-machine deployment. For distributed systems, you'd need a network-aware worker manager.
- **Message types**: `dimos/msgs/` is ROS-flavored. You'd define your own domain types.
- **Backpressure**: The RxPY backpressure implementation (`dimos/rxpy_backpressure/`, 210 LOC) handles fast producers, which matters for real-time streams.

### Patterns Worth Adopting

- **Annotation-driven port declaration** with automatic wiring by name+type
- **Immutable frozen-dataclass builder** for system composition
- **Dual-mode introspection** (class-level for planning, instance-level for runtime)
- **Decorator-based capability tagging** (@rpc, @skill) instead of registration APIs

## Dependencies

| Dependency | Role |
|-----------|------|
| RxPY (reactivex) | Reactive stream operators, observables, backpressure |
| LCM | Inter-process pub/sub transport (multicast UDP) |
| LangChain + LangGraph | Agent state machine, tool binding |
| OpenCV (cv2) | Video capture and processing |
| pydantic | Skill schema validation (legacy system) |
| FastAPI + uvicorn | MCP HTTP server |
| numpy | Array operations |
| cyclonedds | DDS transport option |
| pybind11 | Native module bindings |

## Open Questions

1. **How does the `Configurable` base work?** It's imported from `dimos.protocol.service` but not present in the spec files. Likely provides typed config hydration.

2. **What drives the module-to-worker assignment strategy?** Currently round-robin, but comments suggest GPU-awareness was planned.

3. **How mature is the DDS/Zenoh transport path?** `ZenohTransport` is a one-line stub. `cyclonedds` is imported in transport.py but the `DDSTransport` implementation wasn't visible.

4. **What's the story with `dimos/agents_deprecated/` (5,362 LOC)?** Likely the previous agent system before the Module-based rewrite. Worth checking if any patterns were lost.

5. **How does `dimos/mapping/` (3,956 LOC) work?** Relevant to indoor mapping use cases but not analyzed in this pass.
