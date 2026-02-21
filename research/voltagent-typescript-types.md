---
title: VoltAgent TypeScript Type System Research
date: 2026-03-13
tags: [voltagent, typescript, types, api]
---

# VoltAgent TypeScript Type System Research

Research conducted against the VoltAgent monorepo at `/Users/alphab/Dev/LLM/DEV/helioy/REF/voltagent`. The codebase is a TypeScript-first AI agent framework organized as a pnpm workspace with 30+ packages.

---

## Core Type Definitions

### Agent Configuration: `AgentOptions`

Source: `packages/core/src/agent/types.ts` [641-730]

```typescript
export type AgentOptions = {
  // Identity
  id?: string;
  name: string;
  purpose?: string;

  // Core AI
  model: AgentModelValue;
  instructions: InstructionsDynamicValue;

  // Tools & Memory
  tools?: (Tool<any, any> | Toolkit | VercelTool)[] | DynamicValue<(Tool<any, any> | Toolkit)[]>;
  toolkits?: Toolkit[];
  toolRouting?: ToolRoutingConfig | false;
  workspace?: Workspace | WorkspaceConfig | false;
  workspaceToolkits?: WorkspaceToolkitOptions | false;
  workspaceSkillsPrompt?: WorkspaceSkillsPromptOptions | boolean;
  memory?: Memory | false;
  summarization?: AgentSummarizationOptions | false;
  conversationPersistence?: AgentConversationPersistenceOptions;

  // Retriever/RAG
  retriever?: BaseRetriever;

  // SubAgents
  subAgents?: SubAgentConfig[];
  supervisorConfig?: SupervisorConfig;
  maxHistoryEntries?: number;

  // Hooks
  hooks?: AgentHooks;

  // Guardrails
  inputGuardrails?: InputGuardrail[];
  outputGuardrails?: OutputGuardrail<any>[];

  // Middleware
  inputMiddlewares?: InputMiddleware[];
  outputMiddlewares?: OutputMiddleware<any>[];
  maxMiddlewareRetries?: number;

  // Configuration
  temperature?: number;
  maxOutputTokens?: number;
  maxSteps?: number;
  maxRetries?: number;
  feedback?: AgentFeedbackOptions | boolean;
  stopWhen?: StopWhen;
  markdown?: boolean;
  inheritParentSpan?: boolean;

  // Voice
  voice?: Voice;

  // System
  logger?: Logger;
  voltOpsClient?: VoltOpsClient;
  observability?: VoltAgentObservability;
  context?: ContextInput;

  // Live evaluation
  eval?: AgentEvalConfig;
};
```

### Model Value and Fallback Config

Source: `packages/core/src/agent/types.ts` [236-265]

```typescript
// A single model or a priority-ordered fallback list
export type AgentModelValue = ModelDynamicValue<AgentModelReference> | AgentModelConfig[];

export type AgentModelConfig = {
  id?: string;
  model: ModelDynamicValue<AgentModelReference>;
  maxRetries?: number;
  enabled?: boolean;
};
```

### Tool Definition: `ToolOptions`

Source: `packages/core/src/tool/index.ts` [100-193]

`ToolOptions` is generic over the input schema `T` and optional output schema `O`, both constrained to `ToolSchema` (a Zod schema type).

```typescript
export type ToolOptions<
  T extends ToolSchema = ToolSchema,
  O extends ToolSchema | undefined = undefined,
> = {
  id?: string;
  name: string;
  description: string;
  parameters: T;
  outputSchema?: O;
  tags?: string[];
  needsApproval?: boolean | ToolNeedsApprovalFunction<z.infer<T>>;
  providerOptions?: ProviderOptions;
  toModelOutput?: (args: {
    output: O extends ToolSchema ? z.infer<O> : unknown;
  }) => ToolResultOutput;
  execute?: (
    args: z.infer<T>,
    options?: ToolExecuteOptions,
  ) => ToolExecutionResult<O extends ToolSchema ? z.infer<O> : unknown>;
  hooks?: ToolHooks;
};
```

The `ToolResultOutput` discriminated union supports multimodal returns:

```typescript
export type ToolResultOutput =
  | { type: "text"; value: string }
  | { type: "json"; value: JSONValue }
  | { type: "error-text"; value: string }
  | { type: "error-json"; value: JSONValue }
  | {
      type: "content";
      value: Array<
        { type: "text"; text: string } | { type: "media"; data: string; mediaType: string }
      >;
    };
```

### Dynamic Value Pattern

Source: `packages/core/src/voltops/types.ts` [48-66]

This pattern enables runtime-resolved configuration for instructions, tools, and models:

```typescript
export type PromptHelper = {
  getPrompt: (reference: PromptReference) => Promise<PromptContent>;
};

export interface DynamicValueOptions {
  context: Map<string | symbol, unknown>;
  prompts: PromptHelper;
}

// Generic async resolver — T can be string, Tool[], model reference, etc.
export type DynamicValue<T> = (options: DynamicValueOptions) => Promise<T> | T;
```

### Agent Hooks: `AgentHooks`

Source: `packages/core/src/agent/hooks/index.ts` [215-230]

```typescript
export type AgentHooks = {
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

### Guardrails

Source: `packages/core/src/agent/types.ts`

The guardrail system is bidirectional (input and output) and generic over the output type:

```typescript
export type GuardrailSeverity = "block" | "warn" | "info";
export type GuardrailAction = "block" | "warn" | "pass";

export interface GuardrailDefinition<TArgs, TResult> {
  id?: string;
  name?: string;
  description?: string;
  tags?: string[];
  severity?: GuardrailSeverity;
  metadata?: Record<string, unknown>;
  handler: GuardrailFunction<TArgs, TResult>;
}

export interface InputGuardrailArgs extends GuardrailContext {
  input: string | UIMessage[] | BaseMessage[];
  inputText: string;
  originalInput: string | UIMessage[] | BaseMessage[];
  originalInputText: string;
}

export interface OutputGuardrailArgs<TOutput = unknown> extends GuardrailContext {
  output: TOutput;
  outputText?: string;
  originalOutput: TOutput;
  originalOutputText?: string;
  usage?: UsageInfo;
  finishReason?: string | null;
  warnings?: unknown[] | null;
}
```

### Middleware

Source: `packages/core/src/agent/types.ts` [547-606]

```typescript
export type MiddlewareDirection = "input" | "output";

export interface MiddlewareDefinition<TArgs, TResult> {
  id?: string;
  name?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  handler: MiddlewareFunction<TArgs, TResult>;
}

export interface MiddlewareContext {
  operationContext: OperationContext;
  retryCount: number;
  direction: MiddlewareDirection;
  metadata: Record<string, unknown>;
}
```

### Operation Context

Source: `packages/core/src/agent/types.ts` [1256-1310]

The central per-request context object threaded through all agent operations:

```typescript
export type OperationContext = {
  readonly operationId: string;
  userId?: string;
  conversationId?: string;
  resolvedMemory?: CommonResolvedRuntimeMemoryOptions;
  workspace?: Workspace;
  readonly context: Map<string | symbol, unknown>;
  readonly systemContext: Map<string | symbol, unknown>;
  isActive: boolean;
  parentAgentId?: string;
  elicitation?: (request: unknown) => Promise<unknown>;
  traceContext: AgentTraceContext;
  logger: Logger;
  conversationSteps?: StepWithContent[];
  abortController: AbortController;
  startTime: Date;
  cancellationError?: CancellationError;
  input?: string | UIMessage[] | BaseMessage[];
  output?: string | object;
};
```

### Supervisor / Sub-Agent Config

Source: `packages/core/src/agent/types.ts` [344-386]

```typescript
export type SupervisorConfig = {
  systemMessage?: string;
  includeAgentsMemory?: boolean;
  customGuidelines?: string[];
  fullStreamEventForwarding?: FullStreamEventForwardingConfig;
  throwOnStreamError?: boolean;
  includeErrorInEmptyResponse?: boolean;
};
```

---

## Generic Patterns

### Provider Inference Utilities

Source: `packages/core/src/agent/providers/base/types.ts`

The framework uses `infer`-based conditional types to extract response types from provider implementations without coupling to specific SDKs:

```typescript
// Extract the return type from a provider's generateText method
export type InferGenerateTextResponse<T> = T extends {
  generateText: (...args: any[]) => Promise<infer R>;
}
  ? R
  : unknown;

// Extract provider-specific extra params by subtracting the standard keys
export type InferProviderParams<T> = T extends {
  generateText: (options: infer P) => any;
}
  ? P extends {
      messages: any;
      model: any;
      tools?: any;
      maxSteps?: any;
      schema?: any;
    }
    ? Omit<P, "messages" | "model" | "tools" | "maxSteps" | "schema">
    : Record<string, never>
  : Record<string, never>;

// Cross-provider response inference for public API surface
export type InferGenerateTextResponseFromProvider<TProvider extends { llm: LLMProvider<any> }> =
  ProviderTextResponse<InferOriginalResponseFromProvider<TProvider, "generateText">>;

export type InferGenerateObjectResponseFromProvider<
  TProvider extends { llm: LLMProvider<any> },
  TSchema extends z.ZodType,
> = ProviderObjectResponse<
  InferOriginalResponseFromProvider<TProvider, "generateObject">,
  z.infer<TSchema>
>;
```

### LLMProvider Generic Contract

Source: `packages/core/src/agent/providers/base/types.ts` [422-477]

The provider interface is fully generic, parameterized over the underlying SDK type `TProvider`:

```typescript
export type LLMProvider<TProvider> = {
  generateText(
    options: GenerateTextOptions<InferModel<TProvider>>,
  ): Promise<ProviderTextResponse<InferGenerateTextResponse<TProvider>>>;

  streamText(
    options: StreamTextOptions<InferModel<TProvider>>,
  ): Promise<ProviderTextStreamResponse<InferStreamResponse<TProvider>>>;

  generateObject<TSchema extends z.ZodType>(
    options: GenerateObjectOptions<InferModel<TProvider>, TSchema>,
  ): Promise<ProviderObjectResponse<InferGenerateObjectResponse<TProvider>, z.infer<TSchema>>>;

  streamObject<TSchema extends z.ZodType>(
    options: StreamObjectOptions<InferModel<TProvider>, TSchema>,
  ): Promise<ProviderObjectStreamResponse<InferStreamResponse<TProvider>, z.infer<TSchema>>>;

  toMessage(message: BaseMessage): InferMessage<TProvider>;
  toTool?: (tool: BaseTool) => InferTool<TProvider>;
  getModelIdentifier(model: InferModel<TProvider>): string;
};
```

### Workflow Generic Types

Source: `packages/core/src/workflow/types.ts`

Workflows use four type parameters encoding input, result, suspend, and resume schemas — all constrained to Zod types. This enforces schema-level validation at the type layer:

```typescript
export type WorkflowConfig<
  INPUT_SCHEMA extends InternalBaseWorkflowInputSchema,
  RESULT_SCHEMA extends z.ZodTypeAny,
  SUSPEND_SCHEMA extends z.ZodTypeAny = z.ZodAny,
  RESUME_SCHEMA extends z.ZodTypeAny = z.ZodAny,
> = { ... };

export type Workflow<
  INPUT_SCHEMA extends InternalBaseWorkflowInputSchema,
  RESULT_SCHEMA extends z.ZodTypeAny,
  SUSPEND_SCHEMA extends z.ZodTypeAny = z.ZodAny,
  RESUME_SCHEMA extends z.ZodTypeAny = z.ZodAny,
> = {
  run: (
    input: WorkflowInput<INPUT_SCHEMA>,
    options?: WorkflowRunOptions,
  ) => Promise<WorkflowExecutionResult<RESULT_SCHEMA, RESUME_SCHEMA>>;

  stream: (
    input: WorkflowInput<INPUT_SCHEMA>,
    options?: WorkflowRunOptions,
  ) => WorkflowStreamResult<RESULT_SCHEMA, RESUME_SCHEMA>;

  resume: (
    input: z.infer<RESUME_SCHEMA>,
    options?: { stepId?: string },
  ) => Promise<WorkflowExecutionResult<RESULT_SCHEMA, RESUME_SCHEMA>>;
  // ...
};
```

### Stream Result With Context

Source: `packages/core/src/agent/agent.ts` [526-547]

```typescript
export type StreamTextResultWithContext<
  TOOLS extends ToolSet = Record<string, any>,
  OUTPUT = unknown,
> = {
  readonly text: AIStreamTextResult<TOOLS, any>["text"];
  readonly textStream: AIStreamTextResult<TOOLS, any>["textStream"];
  readonly fullStream: AsyncIterable<VoltAgentTextStreamPart<TOOLS>>;
  readonly usage: AIStreamTextResult<TOOLS, any>["usage"];
  readonly finishReason: AIStreamTextResult<TOOLS, any>["finishReason"];
  readonly partialOutputStream?: AIStreamTextResult<TOOLS, any>["partialOutputStream"];
  toUIMessageStream: AIStreamTextResult<TOOLS, any>["toUIMessageStream"];
  toUIMessageStreamResponse: AIStreamTextResult<TOOLS, any>["toUIMessageStreamResponse"];
  pipeUIMessageStreamToResponse: AIStreamTextResult<TOOLS, any>["pipeUIMessageStreamToResponse"];
  pipeTextStreamToResponse: AIStreamTextResult<TOOLS, any>["pipeTextStreamToResponse"];
  toTextStreamResponse: AIStreamTextResult<TOOLS, any>["toTextStreamResponse"];
  context: Map<string | symbol, unknown>;
  feedback?: AgentFeedbackHandle | null;
} & Record<never, OUTPUT>;
```

---

## Package-level Type Exports

### `@voltagent/core`

Primary type source at `packages/core/src/index.ts`. Key exports:

| Category | Key Types |
|---|---|
| Agent | `Agent`, `AgentOptions`, `AgentHooks`, `AgentStatus`, `AgentResponse`, `AgentFullState` |
| Generation | `GenerateTextOptions`, `StreamTextOptions`, `GenerateObjectOptions`, `StreamObjectOptions` |
| Results | `GenerateTextResultWithContext`, `StreamTextResultWithContext`, `GenerateObjectResultWithContext`, `StreamObjectResultWithContext` |
| Guardrails | `InputGuardrail`, `OutputGuardrail`, `GuardrailDefinition`, `GuardrailAction`, `GuardrailSeverity` |
| Middleware | `InputMiddleware`, `OutputMiddleware`, `MiddlewareDefinition`, `MiddlewareContext` |
| Memory | `MemoryConfig`, `StorageAdapter`, `VectorAdapter`, `EmbeddingAdapter`, `WorkingMemoryConfig` |
| Workflow | `Workflow`, `WorkflowConfig`, `WorkflowRunOptions`, `WorkflowExecutionResult`, `WorkflowStreamResult`, `WorkflowStreamEvent` |
| Provider | `LLMProvider`, `ProviderTextResponse`, `ProviderTextStreamResponse`, `ProviderObjectResponse` |
| Tools | `Tool`, `ToolOptions`, `ToolHooks`, `ToolResultOutput`, `ToolExecuteOptions` |
| Context | `OperationContext`, `UserContext`, `DynamicValue`, `DynamicValueOptions` |
| Operations | `VoltOpsClient`, `VoltOpsClientOptions`, `PromptContent`, `PromptHelper` |

### `@voltagent/internal`

Source: `packages/internal/src/`

Shared primitives used across all packages:

| File | Exports |
|---|---|
| `types/index.ts` | `DangerouslyAllowAny`, `PlainObject`, `Nil`, `AnyFunction`, `AnyAsyncFunction`, `AnySyncFunction` |
| `logger/types.ts` | `Logger`, `LogFn`, `LogLevel`, `LoggerOptions`, `LogEntry`, `LogFilter`, `LogBuffer` |
| `utils/safe-stringify.ts` | `safeStringify`, `SafeStringifyOptions` |
| `mcp/types.ts` | MCP protocol types |
| `a2a/types.ts` | Agent-to-agent protocol types |

### Memory Packages

| Package | Key Exports |
|---|---|
| `@voltagent/libsql` | `LibSQLStorageAdapter`, `LibSQLVectorAdapter`, `LibSQLObservabilityAdapter` |
| `@voltagent/postgres` | `PostgresStorageAdapter`, `PostgresVectorAdapter` |
| `@voltagent/cloudflare-d1` | `CloudflareD1StorageAdapter` |
| `@voltagent/supabase` | `SupabaseStorageAdapter` |

All memory adapters implement the `StorageAdapter` and/or `VectorAdapter` interfaces from `@voltagent/core`.

### Provider Packages

Each AI provider package (`@voltagent/anthropic-ai`, `@voltagent/google-ai`, `@voltagent/groq-ai`) exports a class implementing `LLMProvider<TProvider>`.

---

## Internal Utilities & Shared Types

### `DangerouslyAllowAny`

Source: `packages/internal/src/types/index.ts`

```typescript
/**
 * This type is used to allow any type and bypass restrictions used in
 * typechecking and linting. Provides a CLEAR warning this is NOT the desired
 * behavior and is a dangerous practice.
 */
export type DangerouslyAllowAny = any;
```

This named alias replaces bare `any` usage. The explicit name serves as a lint target and code-review signal — grep for `DangerouslyAllowAny` to audit escape hatches.

### `safeStringify`

Source: `packages/internal/src/utils/safe-stringify.ts`

```typescript
export type SafeStringifyOptions = {
  indentation?: string | number;
};

export function safeStringify(
  input: DangerouslyAllowAny,
  { indentation }: SafeStringifyOptions = {},
): string {
  try {
    const seen = new WeakSet();
    return JSON.stringify(input, safeStringifyReplacer(seen), indentation);
  } catch (error) {
    return `SAFE_STRINGIFY_ERROR: Error stringifying object: ${error instanceof Error ? error.message : "Unknown error"}`;
  }
}
```

`safeStringify` handles circular references via `WeakSet` and returns a fallback error string rather than throwing. **All JSON serialization in the framework must use `safeStringify` — `JSON.stringify` is prohibited by project policy.**

### `Logger` Interface

Source: `packages/internal/src/logger/types.ts`

Defined once in `@voltagent/internal` and consumed by every package:

```typescript
export type LogLevel = "trace" | "debug" | "info" | "warn" | "error" | "fatal" | "silent";
export type LogFn = (msg: string, context?: object) => void;

export interface Logger {
  trace: LogFn;
  debug: LogFn;
  info: LogFn;
  warn: LogFn;
  error: LogFn;
  fatal: LogFn;
  child(bindings: Record<string, any>): Logger;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  msg: string;
  component?: string;
  agentId?: string;
  conversationId?: string;
  workflowId?: string;
  executionId?: string;
  userId?: string;
  [key: string]: any;
}
```

### Utility Types

```typescript
export type PlainObject = Record<string | number | symbol, unknown>;
export type Nil = null | undefined;
export type AnyAsyncFunction = (...args: unknown[]) => Promise<unknown>;
export type AnySyncFunction = (...args: unknown[]) => unknown;
export type AnyFunction = AnyAsyncFunction | AnySyncFunction;
```

---

## Configuration Interfaces

### Memory Configuration

Source: `packages/core/src/memory/types.ts`

```typescript
export interface MemoryConfig {
  storage: StorageAdapter;
  embedding?: EmbeddingAdapterInput;
  vector?: VectorAdapter;
  enableCache?: boolean;
  cacheSize?: number;       // default: 1000
  cacheTTL?: number;        // default: 3600000 (1 hour)
  workingMemory?: WorkingMemoryConfig;
  generateTitle?: boolean | ConversationTitleConfig;
}

export type WorkingMemoryConfig = {
  enabled: boolean;
  scope?: WorkingMemoryScope; // default: 'conversation'
} & (
  | { template: string; schema?: never }
  | { schema: z.ZodObject<any>; template?: never }
  | { template?: never; schema?: never }
);
```

### Workflow Configuration

Source: `packages/core/src/workflow/types.ts`

```typescript
export type WorkflowConfig<
  INPUT_SCHEMA extends InternalBaseWorkflowInputSchema,
  RESULT_SCHEMA extends z.ZodTypeAny,
  SUSPEND_SCHEMA extends z.ZodTypeAny = z.ZodAny,
  RESUME_SCHEMA extends z.ZodTypeAny = z.ZodAny,
> = {
  id: string;
  name: string;
  purpose?: string;
  input?: INPUT_SCHEMA;
  result: RESULT_SCHEMA;
  suspendSchema?: SUSPEND_SCHEMA;
  resumeSchema?: RESUME_SCHEMA;
  hooks?: WorkflowHooks<WorkflowInput<INPUT_SCHEMA>, WorkflowResult<RESULT_SCHEMA>>;
  memory?: Memory;
  logger?: Logger;
  observability?: VoltAgentObservability;
  inputGuardrails?: InputGuardrail[];
  outputGuardrails?: OutputGuardrail<any>[];
  guardrailAgent?: Agent;
  retryConfig?: WorkflowRetryConfig;
  checkpointInterval?: number;
  disableCheckpointing?: boolean;
};

export interface WorkflowRetryConfig {
  attempts?: number;
  delayMs?: number;
}
```

### VoltOps Client Configuration

Source: `packages/core/src/voltops/types.ts`

```typescript
export type VoltOpsClientOptions = {
  baseUrl?: string;
  publicKey?: string;   // pk_ prefix, safe for client-side
  secretKey?: string;   // sk_ prefix, server-side only
  fetch?: typeof fetch;
  prompts?: boolean;
  promptCache?: {
    enabled?: boolean;
    ttl?: number;
    maxSize?: number;
  };
};
```

### Common Generate Options

Source: `packages/core/src/agent/types.ts` [983-1049]

The base interface for all `generateText`, `streamText`, `generateObject`, `streamObject` calls:

```typescript
export interface CommonGenerateOptions {
  provider?: ProviderOptions;
  memory?: CommonRuntimeMemoryEnvelope;

  // Deprecated: use memory.conversationId
  conversationId?: string;
  // Deprecated: use memory.userId
  userId?: string;
  // Deprecated: use memory.options.contextLimit
  contextLimit?: number;

  tools?: BaseTool[];
  maxSteps?: number;
  feedback?: AgentFeedbackOptions | boolean;
  abortController?: AbortController;
  signal?: AbortSignal;   // deprecated, use abortController
  historyEntryId?: string;
  operationContext?: OperationContext;
  context?: UserContext;
  hooks?: AgentHooks;
}
```

### Storage Adapter Interface

Source: `packages/core/src/memory/types.ts` [396-481]

Defines the full persistence contract all storage backends implement:

```typescript
export interface StorageAdapter {
  // Message operations
  addMessage(message: UIMessage, userId: string, conversationId: string, context?: OperationContext): Promise<void>;
  addMessages(messages: UIMessage[], userId: string, conversationId: string, context?: OperationContext): Promise<void>;
  getMessages(userId: string, conversationId: string, options?: GetMessagesOptions, context?: OperationContext): Promise<UIMessage<{ createdAt: Date }>[]>;
  clearMessages(userId: string, conversationId?: string, context?: OperationContext): Promise<void>;
  deleteMessages(messageIds: string[], userId: string, conversationId: string, context?: OperationContext): Promise<void>;

  // Conversation operations
  createConversation(input: CreateConversationInput): Promise<Conversation>;
  getConversation(id: string): Promise<Conversation | null>;
  getConversations(resourceId: string): Promise<Conversation[]>;
  getConversationsByUserId(userId: string, options?: Omit<ConversationQueryOptions, "userId">): Promise<Conversation[]>;
  queryConversations(options: ConversationQueryOptions): Promise<Conversation[]>;
  countConversations(options: ConversationQueryOptions): Promise<number>;
  updateConversation(id: string, updates: Partial<Omit<Conversation, "id" | "createdAt" | "updatedAt">>): Promise<Conversation>;
  deleteConversation(id: string): Promise<void>;

  // Working Memory
  getWorkingMemory(params: { conversationId?: string; userId?: string; scope: WorkingMemoryScope }): Promise<string | null>;
  setWorkingMemory(params: { conversationId?: string; userId?: string; content: string; scope: WorkingMemoryScope }): Promise<void>;
  deleteWorkingMemory(params: { conversationId?: string; userId?: string; scope: WorkingMemoryScope }): Promise<void>;

  // Workflow State
  getWorkflowState(executionId: string): Promise<WorkflowStateEntry | null>;
  queryWorkflowRuns(query: WorkflowRunQuery): Promise<WorkflowStateEntry[]>;
  setWorkflowState(executionId: string, state: WorkflowStateEntry): Promise<void>;
  updateWorkflowState(executionId: string, updates: Partial<WorkflowStateEntry>): Promise<void>;
  getSuspendedWorkflowStates(workflowId: string): Promise<WorkflowStateEntry[]>;
}
```

### Vector and Embedding Adapters

Source: `packages/core/src/memory/adapters/vector/types.ts` and `packages/core/src/memory/adapters/embedding/types.ts`

```typescript
export interface VectorAdapter {
  store(id: string, vector: number[], metadata?: Record<string, unknown>): Promise<void>;
  storeBatch(items: VectorItem[]): Promise<void>;
  search(vector: number[], options?: VectorSearchOptions): Promise<SearchResult[]>;
  delete(id: string): Promise<void>;
  deleteBatch(ids: string[]): Promise<void>;
  clear(): Promise<void>;
  count(): Promise<number>;
  get(id: string): Promise<VectorItem | null>;
}

export interface EmbeddingAdapter {
  embed(text: string): Promise<number[]>;
  embedBatch(texts: string[]): Promise<number[][]>;
  getDimensions(): number | undefined;
  getModelName(): string;
}
```

---

## Response & Stream Types

### Text Generation Response

Source: `packages/core/src/agent/providers/base/types.ts` [44-84]

```typescript
export type ProviderTextResponse<TOriginalResponse> = {
  provider: TOriginalResponse;   // raw SDK response preserved for escape hatch
  text: string;
  usage?: UsageInfo;
  toolCalls?: any[];
  toolResults?: any[];
  finishReason?: string;
  reasoning?: string;
  warnings?: any[];
};

export type UsageInfo = {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  cachedInputTokens?: number;
  reasoningTokens?: number;
};
```

### Text Stream Response

Source: `packages/core/src/agent/providers/base/types.ts` [101-146]

```typescript
export type ProviderTextStreamResponse<TOriginalResponse> = {
  provider: TOriginalResponse;
  textStream: AsyncIterableStream<string>;
  fullStream?: AsyncIterable<StreamPart>;
  text?: Promise<string>;
  finishReason?: Promise<string>;
  usage?: Promise<UsageInfo>;
  reasoning?: Promise<string | undefined>;
};
```

### Stream Finish Result

Source: `packages/core/src/agent/types.ts` [1343-1369]

The object passed to `onFinish` callbacks:

```typescript
export interface StreamTextFinishResult {
  text: string;
  usage?: UsageInfo;
  feedback?: AgentFeedbackMetadata | null;
  finishReason?: string;
  providerResponse?: unknown;
  warnings?: unknown[];
  context?: UserContext;
}

export type StreamTextOnFinishCallback = (result: StreamTextFinishResult) => void | Promise<void>;
```

### Agent Response

Source: `packages/core/src/agent/types.ts` [1120-1139]

```typescript
export type AgentResponse = {
  content: string;
  toolCalls?: ToolCall[];
  metadata: {
    agentId: string;
    agentName: string;
    [key: string]: unknown;
  };
};
```

### Workflow Execution Result

Source: `packages/core/src/workflow/types.ts` [143-165]

```typescript
export interface WorkflowExecutionResult<
  RESULT_SCHEMA extends z.ZodTypeAny,
  RESUME_SCHEMA extends z.ZodTypeAny = z.ZodAny,
> extends WorkflowExecutionResultBase<RESULT_SCHEMA, RESUME_SCHEMA> {
  endAt: Date;
  status: "completed" | "suspended" | "cancelled" | "error";
  result: z.infer<RESULT_SCHEMA> | null;
  suspension?: WorkflowSuspensionMetadata;
  cancellation?: WorkflowCancellationMetadata;
  error?: unknown;
  usage: UsageInfo;
  resume: (
    input: z.infer<RESUME_SCHEMA>,
    options?: { stepId?: string },
  ) => Promise<WorkflowExecutionResult<RESULT_SCHEMA, RESUME_SCHEMA>>;
}
```

### Workflow Stream Result

Source: `packages/core/src/workflow/types.ts` [171-227]

Implements `AsyncIterable<WorkflowStreamEvent>` so callers can `for await` over events:

```typescript
export interface WorkflowStreamResult<
  RESULT_SCHEMA extends z.ZodTypeAny,
  RESUME_SCHEMA extends z.ZodTypeAny = z.ZodAny,
> extends WorkflowExecutionResultBase<RESULT_SCHEMA, RESUME_SCHEMA>,
    AsyncIterable<WorkflowStreamEvent> {
  // Promise-based fields (resolved when stream completes)
  endAt: Promise<Date>;
  status: Promise<"completed" | "suspended" | "cancelled" | "error">;
  result: Promise<z.infer<RESULT_SCHEMA> | null>;
  usage: Promise<UsageInfo>;

  resume: (input: z.infer<RESUME_SCHEMA>, options?: { stepId?: string }) => Promise<WorkflowStreamResult<...>>;
  suspend: (reason?: string) => void;
  cancel: (reason?: string) => void;
  abort: () => void;
  watch: (cb: (event: WorkflowStreamEvent) => void | Promise<void>) => () => void;
  watchAsync: (cb: (event: WorkflowStreamEvent) => void | Promise<void>) => Promise<() => void>;
  observeStream: () => ReadableStream<WorkflowStreamEvent>;
}
```

### Workflow Stream Event

Source: `packages/core/src/workflow/types.ts` [969-1032]

```typescript
export interface WorkflowStreamEvent {
  type: WorkflowStreamEventType;
  executionId: string;
  from: string;
  input?: DangerouslyAllowAny;
  output?: DangerouslyAllowAny;
  status: "pending" | "running" | "success" | "skipped" | "error" | "suspended" | "cancelled";
  context?: UserContext;
  timestamp: string;
  stepIndex?: number;
  stepType?:
    | "agent" | "func" | "conditional-when" | "parallel-all" | "parallel-race"
    | "tap" | "workflow" | "guardrail" | "sleep" | "sleep-until"
    | "foreach" | "loop" | "branch" | "map";
  metadata?: Record<string, DangerouslyAllowAny>;
  error?: DangerouslyAllowAny;
}
```

### Workflow Suspension Metadata

Source: `packages/core/src/workflow/types.ts` [17-41]

```typescript
export interface WorkflowSuspensionMetadata<SUSPEND_DATA = DangerouslyAllowAny> {
  suspendedAt: Date;
  reason?: string;
  suspendedStepIndex: number;
  lastEventSequence?: number;
  suspendData?: SUSPEND_DATA;
  checkpoint?: {
    stepExecutionState?: DangerouslyAllowAny;
    completedStepsData?: DangerouslyAllowAny[];
    workflowState?: WorkflowStateStore;
    stepData?: Record<string, WorkflowCheckpointStepData>;
    usage?: UsageInfo;
  };
}
```

---

## Type Flow Between Packages

```
@voltagent/internal
  └── DangerouslyAllowAny, PlainObject, Nil, AnyFunction
  └── Logger, LogFn, LogLevel, LogEntry, LogFilter, LogBuffer
  └── safeStringify, SafeStringifyOptions
        |
        v
@voltagent/core (packages/core/src/)
  ├── agent/providers/base/types.ts
  │     LLMProvider<TProvider> — generic provider contract
  │     InferModel, InferGenerateTextResponse, InferProviderParams
  │     ProviderTextResponse, ProviderTextStreamResponse
  │     UsageInfo, BaseMessage, BaseTool
  │
  ├── agent/types.ts — 118 exports, 62 downstream consumers
  │     AgentOptions, DynamicValue, OperationContext
  │     GuardrailDefinition, MiddlewareDefinition
  │     CommonGenerateOptions, StreamTextFinishResult
  │
  ├── memory/types.ts — 29 exports, 17 downstream consumers
  │     StorageAdapter, VectorAdapter, EmbeddingAdapter
  │     MemoryConfig, WorkingMemoryConfig, Conversation
  │
  ├── workflow/types.ts — 41 exports, 19 downstream consumers
  │     Workflow<INPUT,RESULT,SUSPEND,RESUME>
  │     WorkflowStreamResult, WorkflowExecutionResult
  │     WorkflowStreamEvent, WorkflowHooks
  │
  └── voltops/types.ts — 120 exports, 19 downstream consumers
        VoltOpsClientOptions, VoltOpsClient, PromptContent
        DynamicValue<T>, DynamicValueOptions, PromptHelper
              |
              v
@voltagent/libsql, @voltagent/postgres, @voltagent/supabase, ...
  (implement StorageAdapter, VectorAdapter)
              |
              v
@voltagent/server-core, @voltagent/server-hono, @voltagent/server-elysia
  (consume Agent, Workflow, Memory interfaces for HTTP API layer)
```

The key design invariant is that `@voltagent/internal` has no dependencies on `@voltagent/core`. Core imports from internal. All other packages import from core (and optionally from internal for logger types). This prevents circular dependencies and keeps the type primitives stable.
