# NOW.md API elaboration

Context: read only verification on `main` at `343a8cc8d365`. `fmm validate` was clean. No code was edited.

## Q1. `/api` router family versus `/v1`

`api/src/transport_matters/main.py create_app` mounts `api/src/transport_matters/api/v1/router.py api_router` at `/api`. That router includes six families: overrides, breakpoint, meta, local file, terminal, and capabilities. The same app also mounts curated `/v1` routes for runs, exchanges, sessions, streams, run meta, and runtime templates.

| `/api` family | What it does and payload | Current consumer evidence | Concern owner today | Desktop status |
| --- | --- | --- | --- | --- |
| `/api/overrides` | Reads, patches, clears, and toggles request override snapshots. Payloads are override arrays plus enabled state, and mutation responses can include audit and curated IR. Query scope accepts `run_id` and `track_id`; backend syncs shared proxy override snapshots when scoped. | `www/src/api.ts fetchOverrides`, `patchOverrides`, `clearOverrides`, `toggleOverrides`; `www/src/hooks/useOverrides.ts useOverrides`; `www/src/components/editor/BreakpointEditorActions.ts` uses the hook. | Concern A current UI. Backend is scoped for shared proxy runs, but the visible consumer is the legacy breakpoint editor. | Not a normal desktop `/canvas` consumer today. Still backend relevant to shared proxy scoped mutation, but no desktop canvas UI currently drives it. |
| `/api/breakpoint` | Controls the pause point: status, paused flow detail, arm, disarm, release edited IR, release unmodified, re audit, and drop. Payloads include breakpoint mode, paused flow summaries, full paused request detail with IR and original request pieces, audit, token counts, and command acknowledgements. | `www/src/api.ts fetchBreakpointStatus`, `armBreakpoint`, `disarmBreakpoint`, `fetchPausedFlowDetail`, `releaseFlow`, `releaseFlowUnmodified`, `dropFlow`, `reauditFlow`; `www/src/hooks/useBreakpoint.ts useBreakpoint`; `www/src/components/editor/BreakpointEditorActions.ts`. | Concern A current UI. | Legacy web app only in current frontend. The desktop canvas has no breakpoint editor route wired to these functions. |
| `/api/meta` | Process scoped backend identity. Payload is `cwd`, `workspace_id`, optional `run_id`, and harness descriptors with command name, binary option, proxy mode, trust requirement, pass through policy, shell env policy, and capabilities. This is not provider exchange metadata and not run event metadata. A run scoped sibling exists at `/v1/runs/{run_id}/meta`. | `www/src/api.ts fetchMeta` uses `/api/meta` when no run id is passed and `/v1/runs/{run_id}/meta` when a run id is passed; `www/src/main.tsx` prefetches meta only when `selectRootRoute` is `legacy`; `www/src/app.tsx BrowserAppShell`, `www/src/hooks/useMeta.ts useMeta`, `www/src/components/editor/BreakpointEditor.tsx`, `www/src/components/routes/OverlaysView.tsx`, and `www/src/components/ExchangeDetail.tsx` consume `useMeta`. | Concern A for `/api/meta`. The `/v1/runs/{run_id}/meta` sibling is the run scoped shape. | `/api/meta` is legacy web app identity. The code has a `/v1` run scoped variant, but current frontend search found no live `fetchMeta(runId)` consumer. |
| `/api/local-file` and `/api/local-file/raw` | Reads an absolute local file as a resource content union. Text, JSON, binary, image, missing, permission, unsupported, and too large outcomes use the resource content response model. Images return a streamed raw URL under `/api/local-file/raw`. | `www/src/session-canvas/api/resourceContent.ts localFileContentPath` and `loadLocalFileContent`; `www/src/session-canvas/hooks/useLocalFileContent.ts useLocalFileContent`; `www/src/session-canvas/viewers/resource/ResourcePane.tsx` renders local path resources through it; `www/src/session-canvas/viewers/resource/ResourcePane.test.tsx` asserts `GET /api/local-file`. | Shared. | Still load bearing for the session canvas resource pane in the desktop client. This is not only legacy web app residue. |
| `/api/terminal` | Generic interactive local shell PTY over WebSocket, with `cols` and `rows`. It spawns a shell in the workspace root and bridges xterm input and PTY output. This is not the captured run terminal. Captured runs attach through `/v1/runs/{runId}/terminal`. | `www/src/session-canvas/viewers/terminal/terminalSocket.ts terminalSocketUrl` builds `/api/terminal`; `www/src/session-canvas/viewers/terminal/TerminalPane.tsx` uses it; `www/src/session-canvas/viewers/registry.tsx` registers the local terminal viewer. `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx` uses `runTerminalSocketUrl`, which targets `/v1/runs/{runId}/terminal`. | Shared canvas utility. | Still load bearing for the session canvas local terminal surface. The captured Claude/Codex pane path is already `/v1`. |
| `/api/capabilities` | Reports installed status for native harness binaries only: per harness `installed`, `path`, and `version`. This endpoint does not read runtime template `capabilities.json` and does not carry `recommended_model`. | `www/src/api.ts fetchCapabilities`; `www/src/session-canvas/lab/capabilitiesStore.ts useCapabilitiesStore`; `www/src/session-canvas/lab/CanvasLabRoute.tsx` gates lab Spawn Claude and Spawn Codex buttons with `harnessInstalled`; `www/src/types/capabilities.ts HarnessCapability`. | Shared, but only the canvas lab currently consumes it. | Load bearing for `/canvas-lab`, not for the normal `/canvas` Agents launcher. It is not the template recommendation source. |

Plain answer: `/api` is not a clean standalone web app control plane and `/v1` is not the only desktop control plane. The current split is mixed:

1. `/api/overrides`, `/api/breakpoint`, and `/api/meta` are legacy standalone web app control surfaces today.
2. `/api/local-file` and `/api/terminal` are genuinely shared session canvas utilities still used by desktop routes.
3. `/api/capabilities` is a harness binary detection utility used by canvas lab, not the runtime template recommendation surface.
4. `/v1` is the curated runs, sessions, exchanges, streams, run meta, and runtime template surface. The normal captured run desktop path uses `/v1/runs` and `/v1/runs/{runId}/terminal`.

So the six `/api` families are not all one unmigrated remainder. Some are legacy web app only, some are shared canvas utilities, and meta already has a run scoped `/v1` sibling.

## Q2. `recommended_model` reader gap

### What `capabilities.py` exposes today

`api/src/transport_matters/capabilities.py HarnessCapability` has only:

| field | meaning |
| --- | --- |
| `installed` | whether the harness binary is runnable |
| `path` | resolved binary path, or null |
| `version` | probed harness version, or null |

`api/src/transport_matters/api/v1/capabilities.py get_capabilities` calls `detect_harnesses` and serializes that shape through `HarnessCapabilityResponse`. `www/src/types/capabilities.ts HarnessCapability` mirrors only `installed`, `path`, and `version`.

### What `recommended_model` looks like

The runtime template domain already defines the schema 2 shape:

| symbol | shape |
| --- | --- |
| `api/src/transport_matters/runtime_templates.py RecommendedModelDefault` | `harness` and `vendor` |
| `api/src/transport_matters/runtime_templates.py RecommendedVendorModel` | `model` and `effort` |
| `api/src/transport_matters/runtime_templates.py RecommendedModel` | `default` plus `by_vendor` |
| `api/src/transport_matters/runtime_templates.py RuntimeTemplateCapabilities` | `schema_version`, `vendors`, `required_capabilities`, `recommended_model`, and `generated_from` |
| `api/src/transport_matters/runtime_templates.py RuntimeTemplateSummary` | `name`, `vendors`, `required_capabilities`, and `recommended_model` |

`api/src/transport_matters/test_runtime_registry.py test_list_runtime_templates_reads_dual_vendor_template` shows a schema 2 `capabilities.json` carrying:

```json
{
  "schema_version": 2,
  "vendors": ["anthropic", "openai"],
  "required_capabilities": [],
  "recommended_model": {
    "default": {"harness": "claude", "vendor": "anthropic"},
    "by_vendor": {
      "anthropic": {"model": "claude-opus-4-8", "effort": "xhigh"},
      "openai": {"model": "gpt-5.5", "effort": "xhigh"}
    }
  },
  "generated_from": "digest"
}
```

`api/src/transport_matters/api/v1/test_runtime_template_routes.py test_runtime_templates_endpoint_response_shape` verifies that `GET /v1/runtime-templates` returns that `recommended_model` shape to the client.

### What the frontend already expects and where it reads from

The Agents launcher does not read `recommended_model` from `/api/capabilities`. It reads runtime templates:

| frontend symbol | role |
| --- | --- |
| `www/src/api.ts fetchRuntimeTemplates` | calls `GET /v1/runtime-templates` |
| `www/src/types/runtimeTemplates.ts RuntimeTemplateSummary` | requires `recommended_model: RecommendedModel | null` |
| `www/src/session-canvas/launcher/useRuntimeTemplates.ts useRuntimeTemplates` | query hook for runtime template rows |
| `www/src/session-canvas/launcher/commandModel.ts templateSpawnHarness` | uses `recommended_model.default.harness` and `recommended_model.default.vendor` to choose the spawn harness |
| `www/src/session-canvas/launcher/commandModel.ts recommendedSubtitle` | uses `recommended_model.by_vendor[vendor].model` and `.effort` for row subtitle |
| `www/src/session-canvas/launcher/commandModel.ts agentSpawnRows` | creates template spawn commands with `runtimeTemplate: template.name` |

### Crisp verdict

`api/src/transport_matters/capabilities.py` is the wrong home for `recommended_model`. Its job is native binary detection for Claude and Codex. The runtime template reader already lives in the correct domain: `api/src/transport_matters/runtime_registry.py read_runtime_template_capabilities` parses schema 2 `capabilities.json`, `api/src/transport_matters/runtime_templates.py RuntimeTemplateSummary` carries `recommended_model`, and `api/src/transport_matters/api/v1/runtime_template_routes.py get_runtime_templates` surfaces it at `GET /v1/runtime-templates`.

The missing reader, as worded, is not missing in current code for the Agents launcher path. If a product surface needs to combine install status with template recommendations, compose those two sources in a launcher specific DTO or in the runtime templates route. Do not grow core `capabilities.py` with template recommendation fields.
