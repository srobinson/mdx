# Transport Matters Provider Surface Deep Dive

Date: 2026-05-15

## Purpose

This note maps the current Transport Matters codebase into horizontal and
vertical surfaces so the staged overlay product can grow without blurring
provider boundaries.

The target product flow is:

1. Screen 0: session inputs that affect the first payload.
2. Screen 1: disposable provider probe.
3. Screen 2: overlay editor from the captured startup payload.
4. Screen 3: fresh working session under the selected overlay.
5. Screen 4: exchange detail, replay, fork, and future overlay tools.

Runtime Matters remains out of scope. Transport Matters owns payload truth,
capture, overlays, replay, fork, and provider transport inspection.

## Product Stance

Use one Transport Matters product and one release line.

Expose provider clients through subcommands and desktop choices:

```text
transport-matters claude
transport-matters codex
transport-matters gemini
```

In code, the missing abstraction is a provider driver. The current
`ProviderAdapter` is a wire format seam. A product driver needs to own launch,
probe, trust, environment, capture, overlay capability, replay, and fork
support.

User facing language should say client. Code and architecture can say driver.
Avoid runtime in Transport Matters naming because Runtime Matters owns runtime
composition.

## Current Topology

The indexed codebase is split into three practical layers:

1. `api/`: 203 files, 41,527 LOC.
2. `www/`: 133 files, 20,077 LOC.
3. `desktop/`: 14 files, 1,560 LOC.

Important subtrees:

1. `api/src/transport_matters/codex/`: Codex vertical, 47 files.
2. `api/src/transport_matters/cli/`: launch and command surface, 37 files.
3. `api/src/transport_matters/storage/`: durable exchange artifacts, 18 files.
4. `api/src/transport_matters/adapters/`: provider wire adapters, 6 files.
5. `www/src/components/`: current UI surface, 74 files.

## Horizontal Surfaces

### CLI Front Door

The package exposes one console script:

```text
transport-matters = transport_matters.cli:main
```

Source: `api/pyproject.toml:47`.

Current commands:

1. `claude`
2. `codex`
3. `doctor`
4. `paths`
5. `list`
6. `version`

The Typer root lives in `api/src/transport_matters/cli/__init__.py:86`.
Provider commands are already separate:

1. `claude` at `api/src/transport_matters/cli/__init__.py:191`.
2. `codex` at `api/src/transport_matters/cli/__init__.py:331`.

This supports a single release with provider subcommands.

### Shared Launch Machinery

`api/src/transport_matters/cli/launch_runtime.py` is the shared launch layer.
It owns:

1. working directory resolution
2. proxy and web ports
3. storage root
4. run id
5. managed environment
6. workspace manifest and lock

Key seams:

1. `resolve_launch_ports` at `launch_runtime.py:119`.
2. `new_run_id` at `launch_runtime.py:194`.
3. `build_launch_env` at `launch_runtime.py:204`.
4. `build_managed_child_env` at `launch_runtime.py:222`.
5. `run_with_workspace_manifest` at `launch_runtime.py:262`.

`build_launch_env` injects `TRANSPORT_MATTERS_STORAGE_DIR`, `WEB_PORT`,
`PROXY_PORT`, `TRANSPORT_MATTERS_RUN_ID`, and `TRANSPORT_MATTERS_CWD`.

`build_managed_child_env` strips proxy and trust variables, then applies managed
proxy variables and `CODEX_CA_CERTIFICATE` when needed. This is a major Screen 0
boundary because these values can change the first captured payload and the
transport path.

### Provider Neutral IR

The common payload model lives in `api/src/transport_matters/ir.py`.

The backend provider contract is currently:

```python
class ProviderAdapter:
    name: str
    def matches(flow) -> bool
    def inbound_request(raw_body) -> InternalRequest
    def outbound_request(ir) -> bytes
    def inbound_response(raw_body, content_type) -> InternalResponse
```

Source: `api/src/transport_matters/adapters/base.py:17`.

Adapter selection is flow based:

1. `get_adapter` at `api/src/transport_matters/adapters/__init__.py:22`.
2. `get_adapter_for_provider` at `api/src/transport_matters/adapters/__init__.py:35`.

Current registry order is Codex first, then Anthropic. That matters because
Codex has HTTP and WebSocket shapes that should not accidentally match generic
HTTP logic.

### Request Pipeline

The horizontal request path is:

```text
provider wire payload
  -> ProviderAdapter.inbound_request
  -> InternalRequest
  -> request pipeline and overrides
  -> curated InternalRequest
  -> ProviderAdapter.outbound_request
  -> provider wire payload
```

`api/src/transport_matters/request_pipeline.py:22` parses raw bytes, classifies
track scope, and applies overrides scoped by `(run_id, track_id)`.

`api/src/transport_matters/flow_state.py:35` joins per flow state:

1. adapter
2. original raw request
3. original IR
4. curated IR
5. audit
6. provisional exchange id
7. track assignment
8. mutation and drop flags
9. Codex header snapshots

This is the current backend ancestor of Screen 1 and Screen 2.

### Storage And Exchange Artifacts

The durable exchange model is `IndexEntry` plus an artifact directory.

`ExchangeArtifacts` at `api/src/transport_matters/storage/base.py:151` stores:

1. original request raw
2. original request IR
3. curated request raw
4. curated request IR
5. request audit
6. response raw
7. response IR
8. transport artifacts
9. Codex semantic events
10. Codex turn summary

`StorageBackend` at `api/src/transport_matters/storage/base.py:275` supports
persisting, reading, deleting, and token backfill. It does not currently model
forks, branches, lineage, or applied overlay ids.

Disk layout at `api/src/transport_matters/storage/disk_layout.py:31` maps an
exchange to:

```text
entry.json
request.raw
request.ir.json
request.curated.raw
request.curated.ir.json
request.audit.json
response.raw
response.ir.json
transport.json
events.jsonl
turn.json
```

This is strong evidence storage, but it is not yet a fork graph.

### API Surface

The FastAPI app mounts `/api` from `api/src/transport_matters/main.py:84`.

The v1 router includes exchanges, overrides, breakpoint, meta, and stream at
`api/src/transport_matters/api/v1/router.py:11`.

Exchange detail response at `api/src/transport_matters/api/v1/exchanges.py:114`
returns:

1. index entry
2. request IR
3. curated request IR
4. request audit
5. response IR
6. transport artifacts
7. Codex events and turn
8. Codex derived artifact state
9. transport diagnostics

`get_exchange` at `api/src/transport_matters/api/v1/exchanges.py:151` reads the
artifact directory and is the backend seed for Screen 4.

### Frontend Shell

`BrowserAppShell` owns the browser state boundary at `www/src/app.tsx:35`.
It manages:

1. persisted UI state
2. exchange list and history lookup
3. stream connection
4. breakpoint mode
5. selected exchange
6. paused flow
7. track collapse state
8. meta

The route model is `intercept`, `overlays`, `trace`, and `recall` at
`www/src/stores/uiStore.ts:16`.

`RouteLayout` stacks the app bar, route rail, and route body at
`www/src/routeLayout.tsx:237`.

The current Intercept route is fixed at a 460px exchange rail plus a main pane at
`www/src/routeLayout.tsx:171`. This is the main cause of the current cramped
layout.

### Existing Overlay UI

The current overlay store is frontend local state.

`Overlay` at `www/src/stores/overlaysStore.ts:29` has:

1. id
2. name
3. scope
4. overrides
5. createdAt
6. draft

`useOverlaysStore` persists overlays at `www/src/stores/overlaysStore.ts:68`.
It stores arrays of current override objects, not durable backend overlays.

The store comments at `www/src/stores/overlaysStore.ts:16` already mark apply at
intercept, chip strips, and per field attribution as future slices.

### Desktop Wrapper

The desktop package is private Electron scaffolding. It hosts the existing web
UI and launches the backend process.

Key files:

1. `desktop/src/backendProcess.ts:60`: builds the backend launch command.
2. `desktop/src/main.ts:81`: chooses desktop client from environment.
3. `desktop/src/window.ts:13`: loads the loopback web UI.

The desktop client type is currently only `claude | codex` at
`desktop/src/backendProcess.ts:5`.

Release CI currently builds the Python wheel with embedded web assets. It does
not package Electron as the primary release artifact.

## Vertical Surface: Claude Code

### Launch

Claude Code is launched through a reverse proxy to Anthropic.

`api/src/transport_matters/cli/start_cmd.py:121` builds:

```text
mitmdump --mode reverse:{upstream}
```

The default upstream is Anthropic. The child environment receives:

```text
ANTHROPIC_BASE_URL=http://127.0.0.1:{proxy_port}
```

Source: `api/src/transport_matters/cli/runner.py:329`.

The CLI also prepends the Transport Matters system prompt with
`--append-system-prompt` unless disabled or already supplied. Source:
`api/src/transport_matters/cli/prompt.py:56`.

### Wire Adapter

`AnthropicAdapter` at `api/src/transport_matters/adapters/anthropic.py:55`
matches `/v1/messages`, parses request JSON to IR, serializes IR back, and
parses JSON or SSE responses.

Claude follows the plain HTTP request and response path. The current backend
can therefore support the disposable probe with less provider specific machinery
than Codex, provided the process can reliably emit the first request.

### Product Implications

Claude is the best first staged overlay target.

Screen 0 needs Claude specific env values and upstream controls that affect the
startup payload.

Screen 1 can reuse the breakpoint and paused flow machinery, but the product
behavior must change:

1. launch a probe instance
2. capture the first request
3. stop the probe immediately
4. send the captured payload into Screen 2

Screen 2 can reuse override and re audit machinery, but should not inherit the
old ARM first journey.

## Vertical Surface: Codex

### Launch

Codex uses an explicit proxy, not Anthropic reverse proxy.

`api/src/transport_matters/cli/codex_cmd.py:208` launches mitmproxy regular mode
and spawns Codex with explicit proxy env.

`build_managed_child_env` at `api/src/transport_matters/cli/launch_runtime.py:222`
sets:

1. HTTP proxy variables
2. HTTPS proxy variables
3. WebSocket proxy variables
4. `NO_PROXY`
5. `CODEX_CA_CERTIFICATE`
6. `CODEX_NETWORK_PROXY_ACTIVE`

Codex also receives a shell environment exclusion policy so commands it runs do
not inherit Transport Matters trust and proxy variables. Source:
`api/src/transport_matters/cli/codex_cmd.py:174`.

### Wire And Transport Adapter

Codex has a deep provider vertical under `api/src/transport_matters/codex/`.

Important pieces:

1. `codex/adapter.py:23`: matches WebSocket and HTTP fallback flows.
2. `codex/transport.py:105`: detects flows and tracks live transport state.
3. `codex/request_parser.py:47`: accepts `response.create` and normalizes to
   `provider="codex"`.
4. `codex/request_serializer.py:33`: preserves HTTP fallback shape.
5. `codex/continuity.py:94`: allocates continuity from headers.

Codex stores derived events and turn sidecars. It also has repair and replay
logic for semantic artifacts, not user facing fork replay.

### Product Implications

Codex needs a richer driver contract than Claude:

1. explicit proxy setup
2. trust bundle creation
3. shell environment exclusion
4. WebSocket and HTTP fallback detection
5. continuity headers
6. sidecar derivation
7. repair diagnostics

Screen 0 for Codex must differ from Claude. It should show proxy, trust, and
fallback controls that can affect the first payload and transport behavior.

The same staged product flow can work, but Codex driver capability flags should
control what the UI offers.

## Future Vertical Surface: Gemini And Other Clients

A future Gemini client can reuse:

1. IR model
2. adapter registry
3. request pipeline
4. override store
5. flow state
6. exchange storage
7. exchange API
8. SSE stream
9. frontend shell
10. desktop host

Required new pieces:

1. provider command or driver registration
2. binary resolution
3. proxy mode
4. managed environment policy
5. trust policy, if needed
6. `ProviderAdapter`
7. tests for matching, parsing, serialization, and persistence

If Gemini is plain HTTP, its vertical can look closer to Claude. If it has
WebSockets, multiplexed turns, or provider diagnostics, it should copy the Codex
vertical shape.

## Missing Abstraction: Driver

Transport Matters should introduce a provider driver layer above
`ProviderAdapter`.

The adapter answers:

```text
How do I parse and serialize provider wire payloads?
```

The driver answers:

```text
How do I run this client through Transport Matters?
```

Suggested driver responsibilities:

1. command name
2. client display name
3. binary resolution
4. proxy mode
5. trust setup
6. child environment
7. shell environment policy
8. pass through policy
9. Screen 0 fields
10. probe support
11. disposable probe shutdown
12. working session launch
13. overlay capability
14. replay capability
15. fork capability
16. exchange detail feature flags

Suggested capability shape:

```text
supports_startup_probe
supports_disposable_probe
supports_overlay_before_work
supports_message_disable
supports_tool_schema_overlay
supports_replay
supports_fork
requires_proxy
requires_trust_bundle
supports_embedded_terminal
supports_transport_diagnostics
```

## Mapping To The Five Screens

### Screen 0: Session Inputs

Current status: missing as a dedicated UI.

Existing code seeds:

1. CLI environment assembly in `launch_runtime.py`.
2. desktop client selection in `desktop/src/main.ts`.
3. meta fetch in `www/src/api.ts`.

Needed:

1. provider aware settings model
2. Screen 0 API or desktop IPC bridge
3. env preview before probe
4. validation for env values that affect capture
5. clear split between Transport Matters capture settings and Runtime Matters
   profile composition

### Screen 1: Disposable Probe

Current status: not present as product behavior.

Existing code seeds:

1. breakpoint pause and hydration
2. flow state and provisional exchange
3. supervisor process lifecycle
4. manifest and run id

Needed:

1. first request capture gate
2. probe run state
3. stop probe after first capture
4. preserve captured payload for Screen 2
5. launch fresh working session after overlay approval

The technical invariant should be:

```text
No user work happens in the probe instance.
```

### Screen 2: Overlay Editor

Current status: partially present through `BreakpointEditor` and local overlay
drafts.

Existing code seeds:

1. override kinds in `api/src/transport_matters/overrides.py:67`
2. TypeScript override kinds in `www/src/types.ts:270`
3. `BreakpointEditor`
4. `TextOverrideEditor`
5. `OverlaysView`
6. re audit and release routes

Needed:

1. durable backend overlay model
2. overlay apply semantics before working launch
3. section level editor for 20k character system prompts
4. Ask Agent flow
5. token delta and risk notes
6. provider locked overlay release

### Screen 3: Working Session

Current status: current Intercept route approximates timeline plus detail, but
not an embedded working session under an overlay.

Existing code seeds:

1. Electron hosted web UI
2. `ExchangeList`
3. `ExchangeTurnCard`
4. exchange stream
5. process supervisor

Needed:

1. fresh working client launch after overlay approval
2. embedded or adjacent terminal surface
3. exchange sidebar that is lighter than current cards
4. active overlay affordance
5. toggle between Claude Code and detail without losing session state

### Screen 4: Exchange Detail

Current status: strongest existing surface.

Existing code seeds:

1. `ExchangeDetail`
2. `InspectTab`
3. `CodexTimeline`
4. `CodexTransportPanel`
5. request and response JSON tabs
6. backend `get_exchange`

Needed:

1. ask agent for analysis
2. explain token weight
3. create future overlay rule
4. replay from here
5. fork from here
6. fork lineage display
7. action rules by exchange age and provider capability

## Forks

Fork management is not present today.

Existing lineage fields are for runs, tracks, subagents, and Codex turns:

1. `run_id`
2. `track_id`
3. `parent_track_id`
4. `track_role`
5. `spawn_anchor`
6. Codex `session_id`
7. Codex `turn_id`
8. Codex `turn_index`

None of these is a user fork graph.

Transport Matters needs a fork model that records:

1. fork id
2. source exchange id
3. source run id
4. source turn index, if provider supplies it
5. source overlay ids
6. changed sections
7. replay or launch command
8. resulting run id
9. resulting exchange lineage

Rules:

1. Past exchanges are immutable evidence.
2. Future payloads are editable.
3. Historical edits produce replay, fork, or future overlay rules.
4. Forks should show as branches in the exchange sidebar, not as mutations of
   the original exchange.

Product phrase:

```text
Inspect past. Shape future. Fork when rewriting history.
```

## Implementation Implications

### Near Term

1. Define provider driver contracts without replacing `ProviderAdapter`.
2. Move Screen 0 configuration into a provider aware model.
3. Add a probe lifecycle for Claude first.
4. Persist captured startup payloads as evidence.
5. Promote overlays from frontend local state to backend durable records.
6. Build a small fork metadata model before implementing replay UI.

### Medium Term

1. Generalize probe lifecycle across Codex.
2. Add capability based UI gating.
3. Add Screen 4 action APIs.
4. Create visual fixtures for all five screens.
5. Package Electron as a first class desktop artifact if the staged flow proves
   valuable.

### Do Not Do Yet

1. Do not split provider binaries.
2. Do not rename provider clients to runtimes inside Transport Matters.
3. Do not make Transport Matters own Runtime Matters profile composition.
4. Do not mutate historical exchange artifacts to represent fork experiments.

## Recommended Next Spec

Write a focused implementation spec for the Claude path:

```text
Screen 0 + disposable Claude probe + durable startup overlay
```

Claude is the right first slice because its transport vertical is simpler than
Codex and the current product discussion centered on `tm claude`.

