---
title: VoltAgent AI Agent System Architecture
date: 2026-03-13
tags: [voltagent, ai-agents, architecture]
---

# VoltAgent AI Agent System

VoltAgent is an open source TypeScript framework for building and orchestrating AI agents. The core package (`packages/core/`) contains 108k LOC across 330 files and provides the Agent class, memory system, tool management, sub-agent orchestration, workflow engine, and observability. The framework directly integrates with the Vercel AI SDK (`ai` package) for all LLM operations, having deprecated its own provider abstraction layer (archived under `archive/deprecated-providers/`).

## Agent Architecture

### Core class: `Agent`

**File:** `packages/core/src/agent/agent.ts` (8175 LOC, 28 public methods)

The `Agent` class is the central construct. It wraps the Vercel AI SDK's `generateText`, `streamText`, `generateObject`, and `streamObject` functions with lifecycle management, memory persistence, guardrails, middleware, tool routing, sub-agent delegation, and OpenTelemetry tracing.

#### Constructor signature

```typescript
constructor(options: AgentOptions)
```

**`AgentOptions`** (defined in `packages/core/src/agent/types.ts`, lines 641-730):

| Group | Fields |
|---|---|
| Identity | `id?`, `name`, `purpose?` |
| Core AI | `model: AgentModelValue`, `instructions: InstructionsDynamicValue` |
| Tools | `tools?`, `toolkits?`, `toolRouting?`, `workspace?`, `workspaceToolkits?`, `workspaceSkillsPrompt?` |
| Memory | `memory?: Memory \| false`, `summarization?`, `conversationPersistence?` |
| RAG | `retriever?: BaseRetriever` |
| Sub-agents | `subAgents?: SubAgentConfig[]`, `supervisorConfig?: SupervisorConfig` |
| Hooks | `hooks?: AgentHooks` |
| Guardrails | `inputGuardrails?`, `outputGuardrails?` |
| Middleware | `inputMiddlewares?`, `outputMiddlewares?`, `maxMiddlewareRetries?` |
| Config | `temperature?`, `maxOutputTokens?`, `maxSteps?`, `maxRetries?`, `stopWhen?`, `markdown?` |
| Voice | `voice?: Voice` |
| System | `logger?`, `voltOpsClient?`, `observability?`, `context?`, `eval?`, `feedback?` |

The constructor initializes five managers:

1. **MemoryManager** (`packages/core/src/memory/manager/memory-manager.ts`) for conversation storage, working memory, and semantic search.
2. **ToolManager** (`packages/core/src/tool/manager/ToolManager.ts`) for static and dynamic tools plus toolkits.
3. **SubAgentManager** (`packages/core/src/agent/subagent/index.ts`) for child agent delegation.
4. **ToolPoolManager** (a second `ToolManager` instance) for tool routing pools.
5. **LoggerProxy** for structured logging with OpenTelemetry context.

#### Four core methods

| Method | Lines | Description |
|---|---|---|
| `generateText(input, options?)` | 995-1493 | Non-streaming text generation |
| `streamText(input, options?)` | 1498-2486 | Streaming text generation |
| `generateObject(input, options?)` | 2492-2814 | Structured object generation with Zod schema |
| `streamObject(input, options?)` | 2820-3290 | Streaming structured object generation |

Each method follows a common execution pipeline:

1. Create `OperationContext` (trace context, userId, conversationId, executionId)
2. Run input middlewares (with retry loop)
3. Run input guardrails
4. Call `prepareExecution()` to assemble messages from memory, resolve model, prepare tools
5. Invoke the corresponding Vercel AI SDK function (`generateText`, `streamText`, etc.)
6. Run output guardrails and output middlewares
7. Persist messages to memory via `ConversationBuffer` and `MemoryPersistQueue`
8. Fire lifecycle hooks (`onEnd`, `onStepFinish`, etc.)
9. Flush observability data

#### `Agent.toTool()` (lines 7961-8029)

Converts an Agent into a `Tool` that can be registered on another Agent, enabling agent-as-tool composition:

```typescript
public toTool(options?: {
  name?: string;
  description?: string;
  parametersSchema?: z.ZodObject<any>;
}): Tool<any, any>
```

The generated tool calls `this.generateText()` internally, passing through operation context for tracing continuity.

#### `AgentFullState` (types.ts, lines 202-221)

```typescript
interface AgentFullState {
  id: string;
  name: string;
  instructions?: string;
  status: string;
  model: string;
  node_id: string;
  tools: ToolWithNodeId[];
  toolRouting?: AgentToolRoutingState;
  subAgents: SubAgentStateData[];
  memory: AgentMemoryState;
  scorers?: AgentScorerState[];
  retriever?: { name: string; description?: string; status?: string; node_id: string; } | null;
  guardrails?: AgentGuardrailStateGroup;
}
```

### VoltAgent orchestrator

**File:** `packages/core/src/voltagent.ts` (850 LOC, 21 public methods)

`VoltAgent` is the top-level application container. Its constructor:

- Initializes `AgentRegistry`, `WorkflowRegistry`, `TriggerRegistry` (all singletons)
- Sets global defaults: memory, tool routing, workspace, observability, logger
- Creates `VoltAgentObservability` (OpenTelemetry instrumentation)
- Registers agents, triggers, and workflows
- Optionally starts an HTTP server (via pluggable `IServerProvider`)
- Sets up graceful shutdown handlers

### AgentRegistry

**File:** `packages/core/src/registries/agent-registry.ts` (311 LOC)

Singleton registry maintaining:

- All registered `Agent` instances (by ID)
- Parent-child agent relationships
- Global defaults: memory, workspace, tool routing, VoltOps client, logger, observability

---

## Memory System

### Memory class

**File:** `packages/core/src/memory/index.ts` (1236 LOC, 45 public methods)

The `Memory` class composes three adapter types:

```typescript
interface MemoryConfig {
  storage: StorageAdapter;          // Required: conversation & message persistence
  embedding?: EmbeddingAdapterInput; // Optional: for semantic operations
  vector?: VectorAdapter;           // Optional: for similarity search
  workingMemory?: WorkingMemoryConfig;
  enableCache?: boolean;
  cacheSize?: number;
  cacheTTL?: number;
  generateTitle?: boolean | ConversationTitleConfig;
}
```

### StorageAdapter interface

**File:** `packages/core/src/memory/types.ts` (lines 396-481)

Defines the contract for message and conversation persistence:

- **Message ops:** `addMessage`, `addMessages`, `getMessages`, `clearMessages`, `deleteMessages`
- **Conversation ops:** `createConversation`, `getConversation`, `getConversations`, `getConversationsByUserId`, `queryConversations`, `countConversations`, `updateConversation`, `deleteConversation`
- **Step ops:** `saveConversationSteps?`, `getConversationSteps?`
- **Working memory ops:** `getWorkingMemory`, `setWorkingMemory`, `deleteWorkingMemory`
- **Workflow state ops:** `getWorkflowState`, `queryWorkflowRuns`, `setWorkflowState`, `updateWorkflowState`, `getSuspendedWorkflowStates`

### Built-in adapters

| Adapter | File | Purpose |
|---|---|---|
| `InMemoryStorageAdapter` | `packages/core/src/memory/adapters/storage/in-memory.ts` | Default in-process storage |
| `InMemoryVectorAdapter` | `packages/core/src/memory/adapters/vector/in-memory.ts` | Default in-process vector store |
| `AiSdkEmbeddingAdapter` | `packages/core/src/memory/adapters/embedding/ai-sdk.ts` | Wraps any Vercel AI SDK embedding model |

### External storage packages

| Package | Exports |
|---|---|
| `@voltagent/libsql` | `LibSQLMemoryAdapter`, `LibSQLVectorAdapter`, `LibSQLObservabilityAdapter` |
| `@voltagent/postgres` | `PostgreSQLMemoryAdapter`, `PostgreSQLVectorAdapter` |
| `@voltagent/supabase` | `SupabaseMemoryAdapter` |
| `@voltagent/cloudflare-d1` | D1 storage adapter (1734 LOC) |
| `@voltagent/voltagent-memory` | `ManagedMemoryAdapter`, `ManagedMemoryVectorAdapter` (managed cloud) |

### Working Memory

**Config** (`WorkingMemoryConfig`, types.ts lines 240-247):

```typescript
type WorkingMemoryConfig = {
  enabled: boolean;
  scope?: WorkingMemoryScope; // 'conversation' | 'user'
} & (
  | { template: string; schema?: never }     // Markdown template
  | { schema: z.ZodObject<any>; template?: never } // Zod schema for JSON
  | { template?: never; schema?: never }     // Free-form
);
```

Working memory allows agents to maintain persistent context across turns. The `Memory.updateWorkingMemory()` method (lines 660-735) supports two modes:

- **replace:** overwrites current working memory
- **append:** merges JSON objects or appends markdown sections

Working memory instructions are injected into the system prompt via `Memory.getWorkingMemoryInstructions()`.

### MemoryManager

**File:** `packages/core/src/memory/manager/memory-manager.ts` (998 LOC, 20 public methods)

Wraps `Memory` with agent-specific concerns:

- `prepareConversationContext()`: loads messages, applies context limits, injects working memory
- `saveMessage()`: queues messages for async persistence
- `searchMessages()`: semantic search across conversation history
- Per-conversation and per-user scoping
- Title generation for new conversations

### Conversation persistence

The agent uses `ConversationBuffer` (`packages/core/src/agent/conversation-buffer.ts`, 561 LOC) as an in-flight accumulator for messages during a single operation. Messages are drained and persisted via `MemoryPersistQueue` after the operation completes.

### Summarization

**File:** `packages/core/src/agent/apply-summarization.ts`

The `applySummarization()` function (174 lines) implements automatic conversation summarization when the message history exceeds configured limits, configured via `AgentSummarizationOptions`.

---

## Tool System

### Tool class

**File:** `packages/core/src/tool/index.ts` (326 LOC)

```typescript
type ToolOptions<T extends ToolSchema, O extends ToolSchema | undefined> = {
  id?: string;
  name: string;
  description: string;
  parameters: T;              // Zod schema for input
  outputSchema?: O;           // Optional Zod schema for output
  tags?: string[];
  needsApproval?: boolean | ToolNeedsApprovalFunction<z.infer<T>>;
  providerOptions?: ProviderOptions;  // e.g., Anthropic cache control
  toModelOutput?: (args) => ToolResultOutput;  // Multi-modal output conversion
  execute?: (args, options?) => ToolExecutionResult<...>;
  hooks?: ToolHooks;
};
```

Factory functions:

- `createTool(options)`: creates a `Tool` instance
- `tool(options)`: alias for `createTool`

### Tool hooks

```typescript
type ToolHooks = {
  onStart?: ToolHookOnStart;     // Before execution
  onEnd?: ToolHookOnEnd;         // After execution (can modify result)
};
```

### Toolkit

**File:** `packages/core/src/tool/toolkit.ts`

```typescript
type Toolkit = {
  name: string;
  description?: string;
  instructions?: string;        // Injected into system prompt when addInstructions=true
  addInstructions?: boolean;
  tools: (Tool<...> | VercelTool)[];
};
```

### Tool routing

**File:** `packages/core/src/tool/routing/types.ts`

```typescript
type ToolRoutingConfig = {
  pool?: (Tool | Toolkit | VercelTool)[];  // Full tool pool
  expose?: (Tool | Toolkit | VercelTool)[]; // Always-visible tools
  embedding?: ToolRoutingEmbeddingInput;    // Embedding model for semantic search
  topK?: number;
  enforceSearchBeforeCall?: boolean;
};
```

Tool routing enables large tool inventories by placing tools in a pool and using embedding-based semantic search (`createEmbeddingToolSearchStrategy` in `packages/core/src/tool/routing/embedding.ts`, 207 LOC) to surface only relevant tools per request.

### ToolManager and BaseToolManager

- **`BaseToolManager`** (`packages/core/src/tool/manager/BaseToolManager.ts`, 254 LOC): generic container managing `Tool[]` and `Toolkit[]` with add/remove/get operations.
- **`ToolManager`** extends `BaseToolManager` with VoltAgent-specific integration.
- **`ToolkitManager`** (`packages/core/src/tool/manager/ToolkitManager.ts`, 48 LOC): manages toolkit lifecycle.

### MCP Tool Integration

**File:** `packages/core/src/mcp/client/index.ts` (620 LOC)

`MCPClient` connects to MCP servers (stdio, SSE, streamable HTTP) and converts MCP tools into VoltAgent `Tool` instances via `getAgentTools()`. Supports `connect()`, `disconnect()`, `callTool()`, `listTools()`, and `listResources()`.

### Reasoning tools

**File:** `packages/core/src/tool/reasoning/index.ts` (182 LOC)

Provides built-in reasoning/planning tools for agents that need structured thinking.

---

## Multi-Agent Orchestration

### SubAgentManager

**File:** `packages/core/src/agent/subagent/index.ts` (959 LOC, 12 public methods)

Manages sub-agent registration and task delegation from a supervisor agent.

#### SubAgentConfig

```typescript
type SubAgentConfig<TAgent extends Agent = Agent> =
  | StreamTextSubAgentConfig<TAgent>
  | GenerateTextSubAgentConfig<TAgent>
  | StreamObjectSubAgentConfig<TAgent>
  | GenerateObjectSubAgentConfig<TAgent>
  | TAgent;  // Direct Agent instance (defaults to streamText)
```

Each variant specifies a `method` (`"streamText"`, `"generateText"`, etc.) and optional method-level options.

#### Task handoff

`SubAgentManager.handoffTask()` (lines 319-580) implements the core delegation flow:

1. Extracts the target `Agent` from config
2. Fires `onHandoff` hook on the target agent
3. Builds a task message with optional shared context
4. Invokes the configured method on the target agent
5. Returns `{ result: string, messages: UIMessage[], usage?: UsageInfo, bailed?: boolean }`

#### Delegate tool generation

`SubAgentManager.createDelegateTool()` (lines 748-872) generates a VoltAgent `Tool` for each sub-agent, allowing the supervisor's LLM to call `delegate_task_to_<agent_name>` tools.

#### Supervisor system message

`SubAgentManager.generateSupervisorSystemMessage()` (lines 236-307) builds a system prompt section describing available sub-agents, their capabilities, and delegation guidelines.

### SupervisorConfig

```typescript
type SupervisorConfig = {
  systemMessage?: string;           // Custom supervisor system message
  includeAgentsMemory?: boolean;    // Include sub-agent memory context (default: true)
  customGuidelines?: string[];
  fullStreamEventForwarding?: FullStreamEventForwardingConfig;
  throwOnStreamError?: boolean;
  includeErrorInEmptyResponse?: boolean;
};
```

### Agent-as-Tool pattern

Via `Agent.toTool()`, any agent can be exposed as a tool on a parent agent without the full SubAgentManager machinery. This provides a simpler composition model when supervisor-style delegation is not required.

### Multi-handoff

`SubAgentManager.handoffToMultiple()` (lines 710-742) executes parallel task handoffs to multiple sub-agents simultaneously.

---

## AI Provider Integrations

### Architecture

VoltAgent uses the **Vercel AI SDK** (`ai` package) as its sole provider layer. The `Agent` class directly imports and calls:

- `generateText()`, `streamText()`, `generateObject()`, `streamObject()` from `ai`
- `UIMessage`, `LanguageModel`, `ToolSet`, `ToolChoice`, `StepResult` types from `ai`
- Utility functions: `convertToModelMessages`, `createUIMessageStream`, `createTextStreamResponse`, `pipeUIMessageStreamToResponse`, `validateUIMessages`, `consumeStream`

### Model resolution

The `model` field on `AgentOptions` accepts `AgentModelValue`, which resolves to a `LanguageModel` from any Vercel AI SDK compatible provider. The agent calls `getModelName()` to extract the model identifier string.

### ModelProviderRegistry

**File:** `packages/core/src/registries/model-provider-registry.ts` (1102 LOC)

Singleton registry that dynamically resolves model providers by ID. Auto-generated from `https://models.dev/api.json`, the registry maps provider IDs to npm packages:

| Provider | npm package | Env vars |
|---|---|---|
| `anthropic` | `@ai-sdk/anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `@ai-sdk/openai` | `OPENAI_API_KEY` |
| `google` | `@ai-sdk/google` | `GOOGLE_GENERATIVE_AI_API_KEY` |
| `amazon-bedrock` | `@ai-sdk/amazon-bedrock` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |
| `azure` | `@ai-sdk/azure` | `AZURE_OPENAI_API_KEY` |
| `mistral` | `@ai-sdk/mistral` | `MISTRAL_API_KEY` |
| (100+ more) | ... | ... |

The registry supports dynamic loading (`resolveLanguageModel`, `resolveEmbeddingModel`), auto-refresh, and runtime provider registration.

### Deprecated provider abstraction

The `LLMProvider<TProvider>` interface (`packages/core/src/agent/providers/base/types.ts`, lines 422-477) defined a provider-agnostic abstraction with methods `generateText`, `streamText`, `generateObject`, `streamObject`, `toMessage`, `toTool`, and `getModelIdentifier`. Concrete implementations for Anthropic, Google, Groq, xsAI, and Vercel AI existed under `archive/deprecated-providers/`. These were replaced by direct Vercel AI SDK integration.

---

## Streaming & Response Handling

### StreamText pipeline

`Agent.streamText()` returns `StreamTextResultWithContext` (lines 526-547):

```typescript
type StreamTextResultWithContext = {
  textStream: AsyncIterableStream<string>;
  fullStream: AsyncIterableStream<VoltAgentTextStreamPart>;
  text: Promise<string>;
  usage: Promise<LanguageModelUsage>;
  finishReason: Promise<FinishReason>;
  response: Promise<{ messages: ModelMessage[] }>;
  steps: Promise<StepResult<ToolSet>[]>;
  consumeStream: () => Promise<void>;
  toTextStreamResponse: (options?: ResponseInit) => Response;
  toUIMessageStreamResponse: (options?: any) => Response;
  pipeTextStreamToResponse: (res: any, init?: ResponseInit) => void;
  pipeUIMessageStreamToResponse: (res: any, init?: any) => void;
  feedback?: AgentFeedbackHandle | null;
};
```

### Guardrail streaming pipeline

**File:** `packages/core/src/agent/streaming/guardrail-stream.ts` (661 LOC)

`createGuardrailPipeline()` wraps a stream with output guardrail processing:

```typescript
type GuardrailPipeline = {
  fullStream: AsyncIterableStream<VoltAgentTextStreamPart>;
  textStream: AsyncIterableStream<string>;
  guardrailPromise: Promise<void>;
  text: Promise<string>;
  response: Promise<{ messages: ModelMessage[] }>;
  steps: Promise<StepResult<ToolSet>[]>;
};
```

Output guardrails can inspect streamed content and trigger actions (block, warn, modify) before the response reaches the consumer.

### UI Message Stream

The framework provides full integration with Vercel AI SDK's `UIMessage` format, enabling:

- `createUIMessageStream()` for server-sent events
- `createUIMessageStreamResponse()` for HTTP response wrapping
- `pipeUIMessageStreamToResponse()` for piping to Node.js responses

### VoltAgentTextStreamPart

**File:** `packages/core/src/agent/subagent/types.ts` (lines 140-179)

A discriminated union extending the AI SDK's stream parts with VoltAgent-specific events for sub-agent delegation, tool calls, and guardrail actions.

---

## Agent Hooks & Events

### AgentHooks interface

**File:** `packages/core/src/agent/hooks/index.ts` (lines 215-230)

```typescript
type AgentHooks = {
  onStart?: AgentHookOnStart;
  onEnd?: AgentHookOnEnd;
  onHandoff?: AgentHookOnHandoff;
  onHandoffComplete?: AgentHookOnHandoffComplete;
  onToolStart?: AgentHookOnToolStart;
  onToolEnd?: AgentHookOnToolEnd;
  onToolError?: AgentHookOnToolError;
  onPrepareMessages?: AgentHookOnPrepareMessages;
  onPrepareModelMessages?: AgentHookOnPrepareModelMessages;
  onError?: AgentHookOnError;
  onStepFinish?: AgentHookOnStepFinish;
  onRetry?: AgentHookOnRetry;
  onFallback?: AgentHookOnFallback;
};
```

### Hook argument types

| Hook | Args type | Key fields |
|---|---|---|
| `onStart` | `OnStartHookArgs` | `agent`, `input`, `context`, `operation` |
| `onEnd` | `OnEndHookArgs` | `agent`, `text`, `usage`, `finishReason`, `responseMessages`, `steps` |
| `onHandoff` | `OnHandoffHookArgs` | `agent`, `sourceAgent` |
| `onHandoffComplete` | `OnHandoffCompleteHookArgs` | `agent`, `sourceAgent`, `result`, `messages`, `usage` |
| `onToolStart` | `OnToolStartHookArgs` | `agent`, `tool`, `args`, `toolCallId` |
| `onToolEnd` | `OnToolEndHookArgs` | `agent`, `tool`, `args`, `result`, `toolCallId` (can return modified result) |
| `onToolError` | `OnToolErrorHookArgs` | `agent`, `tool`, `args`, `error`, `toolCallId` (can return fallback result or rethrow) |
| `onPrepareMessages` | `OnPrepareMessagesHookArgs` | `agent`, `messages` (UIMessage[]), can return modified messages |
| `onPrepareModelMessages` | `OnPrepareModelMessagesHookArgs` | `agent`, `messages` (ModelMessage[]), can return modified model messages |
| `onError` | `OnErrorHookArgs` | `agent`, `error`, `context` |
| `onStepFinish` | `OnStepFinishHookArgs` | `agent`, `step`, `stepNumber` |
| `onRetry` | `OnRetryHookArgs` | `agent`, `context`, `operation`, `source`, `retryCount`, `maxRetries`, `reason` |
| `onFallback` | `OnFallbackHookArgs` | `agent`, `stage`, `targetModel`, `sourceModel`, `reason`, `error` |

### Hook creation

`createHooks(hooks?: Partial<AgentHooks>): AgentHooks` fills missing hooks with no-op defaults.

### Guardrails

**File:** `packages/core/src/agent/guardrail.ts` and `packages/core/src/agent/guardrails/defaults.ts`

Two guardrail types:

- **Input guardrails:** validate/transform input before LLM invocation
- **Output guardrails:** validate/transform output after LLM generation (including during streaming)

```typescript
type GuardrailSeverity = 'error' | 'warning' | 'info';
type GuardrailAction = 'block' | 'warn' | 'log' | 'redact' | 'modify';
```

Built-in guardrail factories: `createDefaultSafetyGuardrails`, `createProfanityGuardrail`, `createPromptInjectionGuardrail`, `createPIIInputGuardrail`, `createHTMLSanitizerInputGuardrail`, `createMaxLengthGuardrail`, and others.

### Middleware

**File:** `packages/core/src/agent/middleware.ts`

Input and output middlewares form a processing pipeline with retry semantics:

```typescript
type InputMiddleware = MiddlewareDefinition & { direction: 'input'; fn: MiddlewareFunction; };
type OutputMiddleware = MiddlewareDefinition & { direction: 'output'; fn: MiddlewareFunction; };
```

Middleware can trigger retries (with configurable `maxMiddlewareRetries`) by throwing errors with specific metadata.

### Observability

All agent operations are instrumented via OpenTelemetry spans. The `VoltAgentObservability` class (`packages/core/src/observability/`) provides:

- Span creation and context propagation
- WebSocket span processor for real-time UI updates
- Serverless-compatible remote export
- Log record correlation with trace context

### Workflow engine

**File:** `packages/core/src/workflow/` (57 files, 18k LOC)

A separate workflow system provides chainable step execution:

- Step types: `andAgent`, `andAll`, `andBranch`, `andForEach`, `andMap`, `andRace`, `andDoWhile`, `andDoUntil`, `andSleep`, `andSleepUntil`, `andGuardrail`
- Suspend/resume support with durable state persistence
- Time-travel debugging
- Workflow registry and lifecycle management

### Additional subsystems

| Subsystem | Location | Purpose |
|---|---|---|
| **RAG** | `packages/rag/` (48 files) | Document chunking (recursive, semantic, markdown, code), utilities |
| **PlanAgent** | `packages/core/src/planagent/` (14 files) | Filesystem-aware planning agent with read/write/search tools |
| **Workspace** | `packages/core/src/workspace/` (29 files) | Sandboxed file system, search, skills, tool policies |
| **Triggers** | `packages/core/src/triggers/` (7 files) | Event-driven agent activation (catalog, DSL, registry) |
| **Scorers** | `packages/scorers/` (22 files) | LLM-based evaluation scorers (answer relevancy, etc.) |
| **Evals** | `packages/evals/` (16 files) | Agent evaluation framework |
| **Voice** | `packages/voice/` (16 files) | Voice I/O integration |
| **MCP Server** | `packages/mcp-server/` (20 files) | Expose agents as MCP servers |
| **A2A Server** | `packages/a2a-server/` (12 files) | Agent-to-agent protocol server |
| **AG-UI** | `packages/ag-ui/` (7 files) | Agent UI protocol |
| **SDK** | `packages/sdk/` (8 files) | Client SDK for consuming VoltAgent APIs |
| **Resumable Streams** | `packages/resumable-streams/` (6 files) | Resumable stream support for Next.js |
