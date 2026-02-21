---
title: VoltAgent Server & API Architecture
date: 2026-03-13
tags: [voltagent, server, api, observability]
---

# VoltAgent Server & API Architecture

Research of the VoltAgent monorepo at `/Users/alphab/Dev/LLM/DEV/helioy/REF/voltagent`. Focuses on server-side components: the HTTP/WebSocket server, all REST endpoints, SSE streaming, OpenTelemetry observability, agent registry, and developer console integration.

Package versions at time of research:
- `@voltagent/server-core` 2.1.10
- `@voltagent/server-hono` 2.0.7

---

## Server Architecture

### Entry Point: `VoltAgent` Class

`/packages/core/src/voltagent.ts`

`VoltAgent` is the top-level bootstrapper. It wires together the agent registry, workflow registry, observability, MCP/A2A servers, and the HTTP server provider.

```typescript
new VoltAgent({
  agents: { myAgent },
  workflows: { myWorkflow },
  memory, agentMemory, workflowMemory,
  observability,          // VoltAgentObservability instance (optional; auto-created)
  voltOpsClient,          // VoltOpsClient for remote telemetry export
  server: (deps) => new HonoServerProvider(deps, { port: 3141 }),
  serverless: (deps) => new HonoServerlessProvider(deps),
  mcpServers: { ... },
  a2aServers: { ... },
  triggers: { ... },
});
```

Constructor flow:
1. Instantiates `AgentRegistry` singleton (global via `globalThis.___voltagent_agent_registry`).
2. Creates or receives a `VoltAgentObservability` instance and sets it on the registry.
3. Auto-configures `VoltOpsClient` from `VOLTAGENT_PUBLIC_KEY` / `VOLTAGENT_SECRET_KEY` env vars if not passed explicitly.
4. Calls `finalizeInit()` which registers agents, triggers, workflows, MCP/A2A servers.
5. If a `server` factory was provided, invokes it with `ServerProviderDeps` and then calls `server.start()`.
6. Exposes `ready: Promise<void>` that resolves when init is complete.

### Server Provider Hierarchy

```
IServerProvider (interface)
  BaseServerProvider (abstract, @voltagent/server-core)
    HonoServerProvider (@voltagent/server-hono)
    ElysiaServerProvider (@voltagent/server-elysia)
```

`BaseServerProvider` handles:
- Port allocation via a singleton `portManager` (tries 3141, 4310, 1337, 4242, then 4300-4400).
- WebSocket server creation and HTTP upgrade wiring.
- SIGINT/SIGTERM graceful shutdown.
- Startup banner printing with discovered endpoint groups.

`HonoServerProvider.start()` additionally:
- Creates the Hono app via `createApp(deps, config, port)`.
- Starts `@hono/node-server` bound to `0.0.0.0` (configurable via `hostname`).
- Instantiates `WebSocketServer` from `ws` and attaches it to the HTTP server for `/ws` upgrades.

### `HonoServerConfig`

`/packages/server-hono/src/types.ts`

```typescript
interface HonoServerConfig {
  port?: number;                 // Default: 3141
  hostname?: string;             // Default: "0.0.0.0"
  enableSwaggerUI?: boolean;     // Default: true in non-production
  cors?: CORSOptions | false;    // Default: allow all origins (*)
  resumableStream?: {
    adapter: ResumableStreamAdapter;
    defaultEnabled?: boolean;
  };
  auth?: AuthProvider;           // Deprecated
  authNext?: AuthNextConfig;     // Preferred auth config
  configureApp?: (app: OpenAPIHonoType) => void | Promise<void>;
  configureFullApp?: (params: { app, routes, middlewares }) => void | Promise<void>;
}
```

### App Factory

`/packages/server-hono/src/app-factory.ts`

`createApp()` builds the Hono `OpenAPIHono` instance. Registration order (default path):
1. CORS middleware (`hono/cors`, allow `*` by default).
2. Auth middleware (if `authNext` or legacy `auth` is configured).
3. Landing page at `GET /`.
4. All route groups: agents, workflows, logs, updates, observability, memory, tools, triggers, MCP, A2A.
5. `GET /doc` - OpenAPI JSON spec.
6. `GET /ui` - Swagger UI (via `@hono/swagger-ui`).
7. Optional `configureApp` callback for custom routes.

`configureFullApp` bypasses all of the above and gives the caller total control.

### `ServerProviderDeps`

`/packages/core/src/types.ts`

The dependency bundle passed to every handler:

```typescript
interface ServerProviderDeps {
  agentRegistry: AgentRegistry;
  workflowRegistry: WorkflowRegistry;
  logger?: Logger;
  voltOpsClient?: VoltOpsClient;
  observability?: VoltAgentObservability;
  mcp?: { registry: MCPServerRegistry };
  a2a?: { registry: A2AServerRegistry };
  triggerRegistry: TriggerRegistry;
  resumableStream?: ResumableStreamAdapter;
  resumableStreamDefault?: boolean;
  ensureEnvironment?: (env?: Record<string, unknown>) => void;
}
```

---

## REST API Reference

All routes defined in `/packages/server-core/src/routes/definitions.ts`. The OpenAPI spec is served at `GET /doc`. Swagger UI at `GET /ui`.

Standard response envelope:
```json
{ "success": true, "data": { ... } }
{ "success": false, "error": "message", "code": "CODE", "httpStatus": 400 }
```

### Agent Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List all registered agents. Returns `id`, `name`, `description`, `status`, `model`, `tools`, `subAgents`, `memory`, `isTelemetryEnabled`. |
| GET | `/agents/:id` | Get single agent details. |

Agent response shape (`AgentResponseSchema`):
```typescript
{
  id: string;
  name: string;
  description: string;
  status: string;        // e.g. "idle" | "working"
  model: string;
  tools: any[];
  subAgents?: SubAgentResponse[];
  memory?: any;
  isTelemetryEnabled: boolean;
}
```

### Agent Generation

All generation endpoints accept a request body validated by `GenerateRequestSchema`. Core fields:

```typescript
{
  input: string | UIMessage[];   // Text prompt or message array
  // Runtime memory envelope (preferred)
  memory?: {
    conversationId?: string;
    userId?: string;
    options?: {
      contextLimit?: number;
      readOnly?: boolean;
      semanticMemory?: { enabled?, semanticLimit?, semanticThreshold?, mergeStrategy? };
      conversationPersistence?: { mode?, debounceMs?, flushOnToolResult? };
    };
  };
  // Deprecated top-level aliases
  conversationId?: string;
  userId?: string;
  contextLimit?: number;
  maxSteps?: number;
  context?: Record<string, unknown>;
  feedback?: FeedbackOptions;
  // Object generation only
  schema?: BasicJsonSchema;
  schemaVersion?: "v3" | "v4";   // zod-from-json-schema version
}
```

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents/:id/text` | Generate text synchronously. Returns `{ text, usage, finishReason, toolCalls, toolResults, feedback?, output? }`. |
| POST | `/agents/:id/stream` | Stream raw AI SDK `fullStream` events via SSE. Full control over text deltas, tool calls, tool results. |
| POST | `/agents/:id/chat` | Stream AI SDK UI messages via SSE. Optimized for `useChat` hook. |
| GET | `/agents/:id/chat/:conversationId/stream` | Resume an in-progress chat stream. Requires `?userId=`. Returns 204 if no active stream. |
| POST | `/agents/:id/object` | Generate a structured object matching `schema`. Returns JSON. |
| POST | `/agents/:id/stream-object` | Stream partial object updates via SSE. |
| GET | `/agents/:id/history` | Paginated execution history for an agent. |

### Agent Workspace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents/:id/workspace` | Workspace capabilities: `{ filesystem, sandbox, search, skills }`. |
| GET | `/agents/:id/workspace/ls` | List files. Query: `path`. |
| GET | `/agents/:id/workspace/read` | Read file content. Query: `path`. |
| GET | `/agents/:id/workspace/skills` | List skills with `active` flag. |
| GET | `/agents/:id/workspace/skills/:skillId` | Skill details including `instructions`. |

### Workflow Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workflows` | List all registered workflows. |
| GET | `/workflows/:id` | Get workflow by ID. |
| GET | `/workflows/executions` | Query executions. Params: `workflowId`, `status`, `from`, `to`, `limit`, `offset`, `userId`, `metadata.*`. |
| POST | `/workflows/:id/execute` | Execute synchronously; returns final result. |
| POST | `/workflows/:id/stream` | Execute with SSE stream. Stream remains open during suspension. |
| GET | `/workflows/:id/executions/:executionId/stream` | Attach to in-progress execution stream. Supports `Last-Event-ID` and `?fromSequence=`. |
| POST | `/workflows/:id/executions/:executionId/suspend` | Suspend running execution. |
| POST | `/workflows/:id/executions/:executionId/cancel` | Cancel execution. Irreversible. |
| POST | `/workflows/:id/executions/:executionId/resume` | Resume suspended execution. Body: `{ resumeData? }`. |
| POST | `/workflows/:id/executions/:executionId/replay` | Deterministic replay from a step. Creates new `executionId`. |
| GET | `/workflows/:id/executions/:executionId/state` | Get execution state (input, suspension info, context, status). |

### Memory API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/memory/conversations` | List conversations. Query: `agentId?`, `resourceId?`, `userId?`. |
| POST | `/api/memory/conversations` | Create conversation. Body: `{ id?, agentId?, userId?, title?, metadata? }`. |
| GET | `/api/memory/conversations/:conversationId` | Get single conversation. |
| PATCH | `/api/memory/conversations/:conversationId` | Update conversation. |
| DELETE | `/api/memory/conversations/:conversationId` | Delete conversation and messages. |
| POST | `/api/memory/conversations/:conversationId/clone` | Clone conversation. |
| GET | `/api/memory/conversations/:conversationId/messages` | List messages. |
| GET | `/api/memory/conversations/:conversationId/working-memory` | Get working memory. |
| POST | `/api/memory/conversations/:conversationId/working-memory` | Update working memory. |
| POST | `/api/memory/save-messages` | Persist messages. |
| POST | `/api/memory/messages/delete` | Delete specific messages by ID. |
| GET | `/api/memory/search` | Semantic search. Query: `q`, `agentId?`, `limit?`, `threshold?`. |

Memory resolution priority: explicit `agentId` query param -> global memory on `AgentRegistry` -> single agent with memory (auto-detected).

### Tools

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools` | List all tools across all agents. Includes `agentId`, `agentName`. |
| POST | `/tools/:name/execute` | Execute tool directly. Body: `{ input, context? }`. |

### Observability

| Method | Path | Description |
|--------|------|-------------|
| POST | `/setup-observability` | Write `VOLTAGENT_PUBLIC_KEY` and `VOLTAGENT_SECRET_KEY` to `.env`. Body: `{ publicKey, secretKey }`. |
| GET | `/observability/traces` | List traces. Query: `entityId?`, `entityType?` (`agent`|`workflow`). |
| GET | `/observability/traces/:traceId` | Get trace with all spans and span tree. |
| GET | `/observability/spans/:spanId` | Get single span. |
| GET | `/observability/status` | Observability system status. |
| GET | `/observability/traces/:traceId/logs` | Logs for a trace. |
| GET | `/observability/spans/:spanId/logs` | Logs for a span. |
| GET | `/observability/logs` | Query logs. Filters: `severity`, time range, `traceId`, etc. |
| GET | `/observability/memory/users` | List users with memory records. |
| GET | `/observability/memory/conversations` | List conversations with agent/user filter. |
| GET | `/observability/memory/conversations/:conversationId/messages` | Messages for a conversation. Supports role filter, `before`/`after` windowing. |
| GET | `/observability/memory/conversations/:conversationId/steps` | Agent steps for a conversation. |
| GET | `/observability/memory/working-memory` | Working memory by conversation or user. |

### Logging

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/logs` | Query structured logs. Filters: `level`, `agentId`, `workflowId`, `conversationId`, `executionId`, time range. |

### System / Updates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/updates` | Check for VoltAgent package updates. |
| POST | `/updates` | Install all updates. Auto-detects pnpm/yarn/npm/bun. |
| POST | `/updates/:packageName` | Install update for a specific package. |

### MCP (Model Context Protocol)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mcp/servers` | List registered MCP servers. |
| GET | `/mcp/servers/:serverId` | Get server metadata. |
| GET | `/mcp/servers/:serverId/tools` | List tools for a server. |
| POST | `/mcp/servers/:serverId/tools/:toolName` | Invoke an MCP tool. Body: `{ arguments }`. |
| POST | `/mcp/servers/:serverId/logging/level` | Set server log level. |
| GET | `/mcp/servers/:serverId/prompts` | List prompts. |
| GET | `/mcp/servers/:serverId/prompts/:promptName` | Get prompt. |
| GET | `/mcp/servers/:serverId/resources` | List resources. |
| GET | `/mcp/servers/:serverId/resources/contents` | Get resource contents. |
| GET | `/mcp/servers/:serverId/resource-templates` | List resource templates. |

MCP transports per server: HTTP (`POST /mcp/:serverId`), SSE (`GET /mcp/:serverId/sse` + `POST /mcp/:serverId/message`), STDIO.

### A2A (Agent-to-Agent)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/.well-known/:serverId/agent-card.json` | Agent Card discovery for A2A protocol. |
| POST | `/a2a/:serverId` | A2A JSON-RPC endpoint. |

---

## WebSocket / SSE Streaming

### SSE (Server-Sent Events)

All streaming agent and workflow endpoints use SSE over HTTP (`Content-Type: text/event-stream`).

SSE frame format (`/packages/server-core/src/utils/sse.ts`):
```
id: <event-id>\n
event: <event-type>\n
data: <json-payload>\n
\n
```

SSE response headers:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Event types emitted by `streamText` (`/agents/:id/stream`):
- `text-delta` - incremental text tokens
- `tool-call` - tool call initiated
- `tool-result` - tool call result
- `finish` - generation complete with `finishReason`, `usage`
- `error` - error condition

`chatStream` (`/agents/:id/chat`) uses the Vercel AI SDK UI message stream protocol with headers from `UI_MESSAGE_STREAM_HEADERS`.

Workflow SSE events:
- Step completion events, suspension events, final result.
- `GET /workflows/:id/executions/:executionId/stream` supports `Last-Event-ID` and `?fromSequence=` for reconnect replay.

### Resumable Streams

`/packages/resumable-streams/`

When `HonoServerConfig.resumableStream` is configured with an adapter, chat streams are stored and can be resumed:
- `POST /agents/:id/chat` - creates a resumable stream; returns `streamId` in response headers.
- `GET /agents/:id/chat/:conversationId/stream?userId=` - resumes the stream for an active conversation.
- Returns 204 if no active stream exists.

### WebSocket

`/packages/server-core/src/websocket/`

WS server attaches to the same HTTP server via `server.on("upgrade")`. Default path prefix: `/ws`.

Supported WebSocket paths:
- `ws://host/ws` - Test/echo connection. Responds with `CONNECTION_TEST` then echoes any message as `ECHO`.
- `ws://host/ws/logs` - Real-time log stream. Query params: `level`, `agentId`, `conversationId`, `workflowId`, `executionId`, `since`, `until`, `limit`. Server pushes log records as they arrive.
- `ws://host/ws/observability` - OpenTelemetry span events bridged from `WebSocketSpanProcessor`. Query params: `entityId`, `entityType`. Messages are pushed as `{ type: "OBSERVABILITY_EVENT", data: ObservabilityWebSocketEvent }`.

WebSocket authentication:
- In development: `x-voltagent-dev: true` header or `?dev=true` bypasses auth.
- Console access: `VOLTAGENT_CONSOLE_ACCESS_KEY` env var; send via `x-console-access-key` header or `?key=`.
- Token auth: `?token=<jwt>` query param, verified by the configured `AuthProvider`.

---

## OpenTelemetry & Observability

### `VoltAgentObservability`

`/packages/core/src/observability/node/volt-agent-observability.ts`

Wraps `NodeTracerProvider` and `LoggerProvider` from the OpenTelemetry SDK. A single global instance is created during `VoltAgent` construction and stored on `AgentRegistry`.

Processor pipeline (in order):
1. `SpanFilterProcessor` - optional scope/service-name filtering.
2. `SamplingWrapperProcessor` - configurable sampling (`always`/`never`/`ratio`/`parent`).
3. `LocalStorageSpanProcessor` - writes spans to `ObservabilityStorageAdapter` (default: `InMemoryStorageAdapter`, max 10,000 spans, 60s cleanup).
4. `WebSocketSpanProcessor` - emits span events to `WebSocketEventEmitter` singleton for real-time WS delivery.
5. `LazyRemoteExportProcessor` - batch exports spans to VoltOps OTLP endpoint when `VOLTAGENT_PUBLIC_KEY`/`VOLTAGENT_SECRET_KEY` are set.
6. Any custom `spanProcessors` from `ObservabilityConfig`.

Log processor pipeline:
1. `StorageLogProcessor` - stores log records in the adapter.
2. `WebSocketLogProcessor` - real-time WS delivery.
3. `RemoteLogProcessor` - batch export to `${voltOpsBaseUrl}/api/public/otel/v1/logs`.
4. Any custom `logProcessors`.

Storage adapter interface (`ObservabilityStorageAdapter`):
```typescript
interface ObservabilityStorageAdapter {
  saveSpan(span: ObservabilitySpan): Promise<void>;
  getTrace(traceId: string): Promise<ObservabilitySpan[]>;
  listTraces(limit, offset, filter?): Promise<string[]>;
  getSpan(spanId: string): Promise<ObservabilitySpan | undefined>;
  saveLogs(records: ObservabilityLogRecord[]): Promise<void>;
  getLogs(filter): Promise<ObservabilityLogRecord[]>;
}
```

`ObservabilitySpan` fields:
```typescript
{
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  name: string;
  kind: SpanKind;         // INTERNAL=0, SERVER=1, CLIENT=2, PRODUCER=3, CONSUMER=4
  startTime: string;      // ISO 8601
  endTime?: string;
  duration?: number;      // ms
  attributes: SpanAttributes;
  status: { code: SpanStatusCode, message?: string };
  events: SpanEvent[];
  links?: SpanLink[];
  resource?: Record<string, any>;
  instrumentationScope?: { name: string; version?: string };
}
```

### VoltOps Remote Export

Auto-configured when env vars are present:
```
VOLTAGENT_PUBLIC_KEY=pk_...
VOLTAGENT_SECRET_KEY=sk_...
```

Traces export to: `${VOLTAGENT_API_URL}/api/public/otel/v1/traces`
Logs export to: `${VOLTAGENT_API_URL}/api/public/otel/v1/logs`

`BatchSpanProcessor` defaults: maxQueueSize=2048, maxExportBatchSize=512, scheduledDelayMillis=5000, exportTimeoutMillis=30000. All configurable via `ObservabilityConfig.voltOpsSync`.

### Serverless Observability

For serverless runtimes (`isServerlessRuntime()` check), `ServerlessVoltAgentObservability` is used instead. It supports the same `serverlessRemote` config and calls `flushOnFinish()` before the response is returned.

### `ObservabilityConfig`

```typescript
interface ObservabilityConfig {
  serviceName?: string;
  serviceVersion?: string;
  instrumentationScopeName?: string;    // Default: "@voltagent/core"
  storage?: ObservabilityStorageAdapter;
  spanFilters?: SpanFilterConfig;       // Restrict by scope name or service name
  flushOnFinishStrategy?: "auto" | "always" | "never";
  voltOpsSync?: { sampling?, maxQueueSize?, maxExportBatchSize?, scheduledDelayMillis?, exportTimeoutMillis? };
  serverlessRemote?: ServerlessRemoteExportConfig;
  spanProcessors?: SpanProcessor[];
  logProcessors?: LogRecordProcessor[];
  resourceAttributes?: Record<string, any>;
}
```

### Real-time WS Observability Bridge

`WebSocketSpanProcessor` emits every completed span as an `ObservabilityWebSocketEvent` through the `WebSocketEventEmitter` singleton. The observability WS handler (`ws://host/ws/observability`) subscribes to this emitter and fans out to connected clients.

Root spans carry `entity.id` and `entity.type` attributes; child spans carry `parentSpanId`. The handler applies entity-level filtering before broadcasting so the developer console can subscribe per agent or workflow.

---

## Agent Registry

`/packages/core/src/registries/agent-registry.ts`

`AgentRegistry` is a true singleton stored on `globalThis.___voltagent_agent_registry` to survive module duplication in monorepos and Next.js.

Key methods:
```typescript
AgentRegistry.getInstance(): AgentRegistry

registerAgent(agent: Agent): void
getAgent(id: string): Agent | undefined
getAllAgents(): Agent[]
removeAgent(id: string): boolean
getAgentCount(): number

registerSubAgent(parentId: string, childId: string): void
unregisterSubAgent(parentId: string, childId: string): void
getParentAgentIds(childId: string): string[]

setGlobalObservability(obs: VoltAgentObservability): void
setGlobalVoltOpsClient(client: VoltOpsClient): void
setGlobalMemory(memory: Memory): void
setGlobalAgentMemory(memory: Memory): void
setGlobalWorkflowMemory(memory: Memory): void
setGlobalWorkspace(workspace: Workspace): void
setGlobalToolRouting(config: ToolRoutingConfig): void
setGlobalLogger(logger: Logger): void
```

`Agent` instances self-register by calling `AgentRegistry.getInstance().registerAgent(this)` during construction. Sub-agent relationships are tracked in a separate `agentRelationships: Map<childId, parentId[]>` for UI hierarchy display.

---

## Developer Console

The developer console is the hosted web UI at `https://console.voltagent.dev`. It connects to a locally running VoltAgent server via WebSocket and REST.

### Landing Page

`GET /` returns an HTML page (`getLandingPageHTML()`) that directs users to connect the console. It includes the local server URL so the console can be pointed at it directly.

### Console Authentication

When `authNext` is configured, console routes are separated from user routes:

Console routes (require `VOLTAGENT_CONSOLE_ACCESS_KEY` or dev bypass):
- `GET /agents`, `GET /agents/:id`
- `GET /workflows`, `GET /workflows/:id`
- `GET /tools`
- `GET /doc`, `GET /ui`, `GET /`
- `GET /mcp/servers`, `GET /mcp/servers/:serverId`, `GET /mcp/servers/:serverId/tools`
- All observability routes (inferred from WS handler)

Dev bypass: `x-voltagent-dev: true` header (only effective when `NODE_ENV !== "production"`). `?dev=true` query param works the same way for WebSocket connections.

Console access key: `VOLTAGENT_CONSOLE_ACCESS_KEY` env var. Send as `x-console-access-key` header or `?key=` query param.

### WebSocket Protocol for Console

The console subscribes to:
1. `ws://localhost:PORT/ws/observability?entityId=<agentId>&entityType=agent` for live trace/span events.
2. `ws://localhost:PORT/ws/logs?agentId=<agentId>` for live log entries.

Messages from server:
```json
{ "type": "OBSERVABILITY_EVENT", "success": true, "data": { "span": ObservabilitySpan, ... } }
```

### OpenAPI / Swagger UI

- Spec: `GET /doc` - returns OpenAPI 3.1.0 JSON with all registered routes.
- UI: `GET /ui` - Swagger UI, enabled by default in non-production, disabled in `NODE_ENV=production` unless explicitly set.

`getEnhancedOpenApiDoc()` introspects the Hono router to include custom routes registered via `configureApp`.

---

## Configuration & Deployment

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `VOLTAGENT_PUBLIC_KEY` | VoltOps public key for remote observability export |
| `VOLTAGENT_SECRET_KEY` | VoltOps secret key for remote observability export |
| `VOLTAGENT_CONSOLE_ACCESS_KEY` | Protects console routes (WebSocket and HTTP) |
| `NODE_ENV` | `production` disables Swagger UI and dev bypasses |
| `VOLTAGENT_API_URL` | Override VoltOps API base URL (default: `https://api.voltagent.dev`) |

Keys can be written to `.env` at runtime via `POST /setup-observability`. Server restart is required for new keys to take effect.

### Port Selection

Default port: **3141** (pi-inspired). Falls back through 4310, 1337, 4242, then 4300-4400. Specify explicitly via `HonoServerConfig.port`.

### Node vs Serverless

Node deployment uses `HonoServerProvider` (starts a persistent HTTP server).

Serverless deployment uses a provider factory passed as `serverless: (deps) => provider`. The resulting object exposes:
```typescript
provider.handleRequest(request: Request): Promise<Response>
provider.toCloudflareWorker(): { fetch: CloudflareFetchHandler }
provider.toVercelEdge(): ServerlessRequestHandler
provider.toDeno(): ServerlessRequestHandler
provider.auto(): CloudflareHandler | RequestHandler
```

### Multi-framework Support

`@voltagent/server-core` is framework-agnostic. It exports all handlers, route definitions, schemas, SSE utilities, WebSocket utilities, and auth primitives. Framework adapters import from it:
- `@voltagent/server-hono` - Hono (primary implementation)
- `@voltagent/server-elysia` - Bun/Elysia
- `@voltagent/serverless-hono` - Cloudflare Workers / Vercel Edge

### Graceful Shutdown

`BaseServerProvider.setupGracefulShutdown()` intercepts SIGINT and SIGTERM, calls `stop()` which closes the WebSocket server then calls the framework-specific `stopServer()`, and exits with code 0.

Port manager tracks allocated ports and releases them on stop to allow clean restart in the same process.

### CORS

Default config: `origin: "*"`, methods `GET POST PUT DELETE OPTIONS`, headers `Content-Type Authorization`, credentials `true`.

Set `cors: false` in `HonoServerConfig` to disable global CORS and configure per-route via `configureApp`.

### Resumable Streams

Pass a `ResumableStreamAdapter` to persist active chat streams across connection drops. The adapter interface:
```typescript
interface ResumableStreamAdapter {
  createStream(params: { conversationId, agentId?, userId, stream, metadata? }): Promise<string>; // streamId
  resumeStream(streamId: string): Promise<ReadableStream<string> | null>;
  getActiveStreamId(params: { conversationId, agentId?, userId }): Promise<string | null>;
  clearActiveStream(params: { conversationId, agentId?, userId, streamId? }): Promise<void>;
}
```

---

## Key File Paths

| Path | Contents |
|------|---------|
| `/packages/core/src/voltagent.ts` | Top-level `VoltAgent` class |
| `/packages/core/src/registries/agent-registry.ts` | `AgentRegistry` singleton |
| `/packages/core/src/observability/node/volt-agent-observability.ts` | OTel provider wrapper |
| `/packages/core/src/observability/types.ts` | `ObservabilitySpan`, `ObservabilityConfig`, etc. |
| `/packages/core/src/types.ts` | `VoltAgentOptions`, `ServerProviderDeps`, response types |
| `/packages/server-core/src/server/base-provider.ts` | `BaseServerProvider` |
| `/packages/server-core/src/routes/definitions.ts` | All route definitions |
| `/packages/server-core/src/schemas/agent.schemas.ts` | Zod validation schemas |
| `/packages/server-core/src/handlers/agent.handlers.ts` | Agent request handlers |
| `/packages/server-core/src/handlers/observability.handlers.ts` | Trace/span query handlers |
| `/packages/server-core/src/websocket/setup.ts` | WS server creation and auth |
| `/packages/server-core/src/websocket/handlers.ts` | WS path dispatch |
| `/packages/server-core/src/websocket/observability-handler.ts` | OTel-to-WS bridge |
| `/packages/server-core/src/utils/sse.ts` | SSE formatting utilities |
| `/packages/server-core/src/auth/types.ts` | `AuthProvider` interface |
| `/packages/server-core/src/auth/next.ts` | `AuthNextConfig`, route access resolution |
| `/packages/server-core/src/auth/defaults.ts` | Default public and console routes |
| `/packages/server-hono/src/hono-server-provider.ts` | `HonoServerProvider` |
| `/packages/server-hono/src/app-factory.ts` | `createApp()` |
| `/packages/server-hono/src/types.ts` | `HonoServerConfig` |
