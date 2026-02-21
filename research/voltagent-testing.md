---
title: VoltAgent Testing Strategy & Patterns
date: 2026-03-13
tags: [voltagent, testing, qa, vitest]
---

# VoltAgent Testing Strategy & Patterns

Comprehensive QA reference for the VoltAgent monorepo. Covers framework setup, patterns, utilities, and CI integration derived from direct inspection of 190+ spec files across 30+ packages.

## Testing Philosophy

VoltAgent testing follows a **co-location principle**: every test file lives next to the source it covers, sharing the same base name (`tool.ts` → `tool.spec.ts`). The framework avoids mocking the entire AI SDK; instead it leans on the SDK's own `ai/test` package (`MockLanguageModelV3`, `simulateReadableStream`) to produce realistic, type-safe model responses without real API calls.

The guiding priorities are:

1. Prevent defects at the boundary with the AI SDK (model inputs/outputs, streaming)
2. Type safety as a first-class test artifact (`.spec-d.ts` files run `expectTypeOf` assertions)
3. Deterministic, fast unit tests — timeouts are capped at 10 seconds
4. Integration tests scoped to specific subsystems (memory persistence, guardrails) rather than full end-to-end flows

## Test Framework & Setup

### Runtime

- **Framework**: Vitest (not Jest)
- **Coverage provider**: V8
- **Environment**: Node.js for all packages
- **Globals**: enabled (`describe`, `it`, `expect`, `vi` available without imports in spec files, though explicit imports are used in practice)
- **Timeouts**: 10 000 ms per test, 10 000 ms per hook

### Vitest Config (canonical — packages/core)

```typescript
// packages/core/vitest.config.mts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["**/*.spec.ts"],
    environment: "node",
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.d.ts", "src/**/index.ts"],
    },
    typecheck: {
      include: ["**/**/*.spec-d.ts"],
      exclude: ["**/**/*.spec.ts"],
    },
    globals: true,
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
```

Every package carries its own `vitest.config.mts` (or `.ts`). The root `package.json` script `test:all` uses Lerna to fan-out across all `@voltagent/*` scopes:

```bash
pnpm test:all                        # all packages
pnpm test:all:coverage               # with V8 coverage
pnpm test --filter @voltagent/core   # single package
cd packages/core && pnpm vitest run src/tool/index.spec.ts  # single file
```

### File Naming Convention

| File pattern | Purpose |
|---|---|
| `*.spec.ts` | Unit and integration tests |
| `*.spec-d.ts` | Type-level tests (`expectTypeOf`) |
| `*.integration.spec.ts` | Integration tests (informal naming convention) |
| `*.e2e.spec.ts` | End-to-end tests in `packages/e2e` |

## Unit Testing Patterns

### Baseline structure

All tests follow the Arrange / Act / Assert pattern with descriptive `describe` nesting:

```typescript
import { describe, expect, it, vi } from "vitest";
import { yourFunction } from "./index";

describe("YourClass", () => {
  describe("methodName", () => {
    it("should <expected behavior>", () => {
      // Arrange
      const instance = new YourClass();

      // Act
      const result = instance.methodName();

      // Assert
      expect(result).toBe("expected");
    });
  });
});
```

### Testing Tools

Tools are pure value objects — test them without mocking anything:

```typescript
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { Tool, createTool } from "./index";

describe("Tool", () => {
  it("should initialize with provided options", () => {
    const tool = new Tool({
      id: "test-tool-id",
      name: "testTool",
      description: "A test tool",
      parameters: z.object({ param1: z.string() }),
      execute: vi.fn(),
    });

    expect(tool.id).toBe("test-tool-id");
    expect(tool.name).toBe("testTool");
  });

  it("should default id to name when id is not provided", () => {
    const tool = new Tool({
      name: "testTool",
      parameters: z.object({}),
      description: "A test tool",
      execute: vi.fn(),
    });

    expect(tool.id).toBe("testTool");
  });

  it("should detect invalid output when schema is provided", async () => {
    const outputSchema = z.object({ result: z.string(), count: z.number() });

    const tool = createTool({
      name: "invalidOutputTool",
      description: "A tool that returns invalid output",
      parameters: z.object({ text: z.string() }),
      outputSchema,
      execute: async ({ text }) => ({
        result: text.toUpperCase(),
        count: "invalid" as any, // intentionally wrong type
      }),
    });

    const result = await tool.execute?.({ text: "test" });
    const parseResult = tool.outputSchema?.safeParse(result);
    expect(parseResult?.success).toBe(false);
    expect(parseResult?.error?.errors?.[0]?.message).toContain("Expected number");
  });
});
```

### Testing Agents

The correct approach uses `MockLanguageModelV3` from `ai/test` and then mocks the AI SDK functions via `vi.mock("ai", ...)` while preserving core converters:

```typescript
import { MockLanguageModelV3 } from "ai/test";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Agent } from "./agent";

// Preserve core converters, mock only generation functions
vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,
    generateText: vi.fn(),
    streamText: vi.fn(),
    generateObject: vi.fn(),
    streamObject: vi.fn(),
    stepCountIs: vi.fn(() => vi.fn(() => false)),
  };
});

describe("Agent", () => {
  let mockModel: MockLanguageModelV3;

  beforeEach(() => {
    mockModel = new MockLanguageModelV3({
      modelId: "test-model",
      doGenerate: {
        content: [{ type: "text", text: "Test response" }],
        finishReason: "stop",
        usage: {
          inputTokens: 10,
          outputTokens: 5,
          totalTokens: 15,
          inputTokenDetails: { noCacheTokens: 10, cacheReadTokens: 0, cacheWriteTokens: 0 },
          outputTokenDetails: { textTokens: 5, reasoningTokens: 0 },
        },
        warnings: [],
      },
    });

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should create agent with required fields", () => {
    const agent = new Agent({
      name: "TestAgent",
      instructions: "Test instructions",
      model: mockModel as any,
    });

    expect(agent.name).toBe("TestAgent");
    expect(agent.id).toBeDefined();
  });
});
```

### Testing Memory Providers

Memory tests use the real `InMemoryStorageAdapter` plus shared test fixtures from `src/memory/test-utils.ts`:

```typescript
import { beforeEach, describe, expect, it } from "vitest";
import { ConversationAlreadyExistsError } from "../../errors";
import {
  createTestConversation,
  createTestMessages,
  createTestUIMessage,
} from "../../test-utils";
import { InMemoryStorageAdapter } from "./in-memory";

describe("InMemoryStorageAdapter", () => {
  let storage: InMemoryStorageAdapter;

  beforeEach(() => {
    storage = new InMemoryStorageAdapter();
  });

  it("should throw ConversationAlreadyExistsError for duplicate IDs", async () => {
    const input = createTestConversation({ id: "duplicate-id" });
    await storage.createConversation(input);

    await expect(storage.createConversation(input)).rejects.toThrow(
      ConversationAlreadyExistsError,
    );
  });

  it("should deep clone the conversation object", async () => {
    const input = createTestConversation({
      metadata: { nested: { value: "test" } },
    });

    await storage.createConversation(input);

    // Mutate original; stored copy must be unaffected
    (input.metadata as any).nested.value = "modified";
    const retrieved = await storage.getConversation(input.id);

    expect((retrieved?.metadata as any)?.nested?.value).toBe("test");
  });
});
```

### Type-Level Tests

The `.spec-d.ts` files exercise the TypeScript type system directly using `expectTypeOf`. They use `MockLanguageModelV3` to construct valid instances, then assert on inferred types:

```typescript
// agent.spec-d.ts
import { MockLanguageModelV3 } from "ai/test";
import { describe, expectTypeOf, it } from "vitest";
import { Agent } from "./agent";
import type { GenerateTextResultWithContext } from "./agent";

describe("Agent Type System", () => {
  const mockModel = new MockLanguageModelV3({
    doGenerate: async () => ({
      finishReason: { unified: "stop", raw: "stop" },
      usage: { inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
               outputTokens: { total: 20, text: 20, reasoning: 0 } },
      content: [{ type: "text" as const, text: "test response" }],
      warnings: [],
    }),
    doStream: async () => ({ stream: {} as ReadableStream<any> }),
  });

  it("generateText result should include context", () => {
    const agent = new Agent({ name: "test", model: mockModel as any, instructions: "" });
    expectTypeOf(agent.generateText).returns.resolves.toMatchTypeOf<{
      context: Map<string | symbol, unknown>;
    }>();
  });
});
```

## Integration Testing

Integration specs are named with `.integration.spec.ts` to make their scope visible. They construct real collaborating objects (no mocks for the wiring under test) and only stub external boundaries.

### Memory Persistence Integration Pattern

```typescript
// agent/memory-persistence.integration.spec.ts
import { describe, expect, it, vi } from "vitest";
import { ConversationBuffer } from "./conversation-buffer";
import { MemoryPersistQueue } from "./memory-persist-queue";

// Local helper — not from test-utils — because this spec owns its test context
const createLogger = () => {
  const logger = { debug: vi.fn(), error: vi.fn() };
  logger.child = vi.fn().mockReturnValue(logger);
  return logger;
};

describe("Conversation persistence integration", () => {
  it("persists OpenAI-style tool call/result sequence as a single assistant message", async () => {
    const memoryManager = { saveMessage: vi.fn().mockResolvedValue(undefined) };

    const buffer = new ConversationBuffer(undefined, createLogger() as any);
    const queue = new MemoryPersistQueue(memoryManager as any, {
      debounceMs: 0,
      logger: createLogger() as any,
    });

    // Exercise the interaction between ConversationBuffer and MemoryPersistQueue
    // with realistic ModelMessage shapes
  });
});
```

### Guardrail Integration

Integration tests for guardrails wire a real `Agent` with `createMockLanguageModel()` and real `createOutputGuardrail()` instances, asserting on the combined output:

```typescript
import { describe, expect, it, vi } from "vitest";
import { Agent } from "./agent";
import { createOutputGuardrail } from "./guardrail";
import { createMockLanguageModel, defaultMockResponse } from "./test-utils";

describe("Agent guardrail integration", () => {
  it("sanitizes generateText output through a chain of guardrails", async () => {
    const model = createMockLanguageModel({
      doGenerate: {
        ...defaultMockResponse,
        content: [{ type: "text", text: "Funding: $987 million USD" }],
      },
    });

    const agent = new Agent({
      name: "Guarded Agent",
      instructions: "Return funding details.",
      model,
      outputGuardrails: [
        createOutputGuardrail({
          id: "funding-filter",
          name: "Funding Filter",
          handler: vi.fn(async ({ outputText }) => ({
            pass: true,
            action: "modify",
            modifiedOutput: (outputText as string).replace(/\$\d[\d.,]*/gi, "$[redacted]"),
          })),
        }),
      ],
    });

    const result = await agent.generateText("How much funding?");

    expect(result.text).toBe("Funding: $[redacted] million USD");
    expect(result.usage).toEqual(defaultMockResponse.usage);
  });
});
```

### E2E Tests (packages/e2e)

End-to-end specs require real database instances. The CI matrix spins up a Postgres service container. E2E tests use the real `@voltagent/core` agent and actual storage adapters:

- `message-persistence.postgres.e2e.spec.ts`
- `message-persistence.libsql.e2e.spec.ts`

Shared assertions live in `message-persistence.shared.ts`, consumed by both adapters to keep behavior parity:

```typescript
// packages/e2e/src/message-persistence.shared.ts
import { Agent, createTool } from "@voltagent/core";
import { MockLanguageModelV3 } from "ai/test";
import { expect, vi } from "vitest";

export const assertAssistantParts = (message: UIMessage, turnNumber: number) => {
  // Shared assertion logic reused across postgres and libsql tests
};
```

## Mocking Strategies

### Strategy 1: MockLanguageModelV3 (preferred for agent tests)

Use `ai/test`'s `MockLanguageModelV3` for deterministic model responses. It implements the full `LanguageModel` interface:

```typescript
import { MockLanguageModelV3, simulateReadableStream } from "ai/test";

// For generateText
const model = new MockLanguageModelV3({
  doGenerate: async () => ({
    finishReason: { unified: "stop", raw: "stop" },
    usage: {
      inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
      outputTokens: { total: 5, text: 5, reasoning: 0 },
    },
    content: [{ type: "text", text: "Mock response" }],
    warnings: [],
  }),
});

// For streamText
const streamingModel = new MockLanguageModelV3({
  doStream: async () => ({
    stream: simulateReadableStream({
      chunks: [
        { type: "text-start", id: "text-1" },
        { type: "text-delta", id: "text-1", delta: "Hello " },
        { type: "text-delta", id: "text-1", delta: "world" },
        { type: "text-end", id: "text-1" },
        { type: "finish", finishReason: { unified: "stop", raw: "stop" },
          usage: { inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
                   outputTokens: { total: 5, text: 5, reasoning: 0 } } },
      ],
    }),
  }),
});
```

### Strategy 2: Module-level vi.mock (for AI SDK boundary isolation)

When testing agent internals that call `generateText`/`streamText` directly, mock the entire AI SDK while preserving converters:

```typescript
vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,           // keep convertToCoreMessages, etc.
    generateText: vi.fn(),
    streamText: vi.fn(),
    generateObject: vi.fn(),
    streamObject: vi.fn(),
  };
});
```

### Strategy 3: vi.spyOn for method-level stubs

`createMockAgentWithStubs()` (in `agent/subagent/test-utils.ts`) uses `vi.spyOn` to replace individual agent methods while keeping the real constructor and type structure:

```typescript
vi.spyOn(agent, "generateText").mockImplementation(async (_input, _options) => ({
  text: `Response from ${agent.name}`,
  usage: createMockUsage(),
  context: new Map(),
  // ... full return shape
}));
```

### Strategy 4: External module mocks

```typescript
// Mock uuid for deterministic IDs
vi.mock("uuid", () => ({
  v4: vi.fn().mockReturnValue("mock-uuid"),
}));
```

## Test Utilities

### packages/core/src/agent/test-utils.ts

The primary utility module. Exported functions:

| Function | Purpose |
|---|---|
| `createMockLanguageModel(config?)` | Creates a `LanguageModel` wrapping `MockLanguageModelV3` with normalized usage/finishReason shapes |
| `createTestAgent(options?)` | Creates an `Agent` with safe defaults for unit tests |
| `createMockTool(name, execute?, options?)` | Creates a `Tool` instance with a default Zod schema |
| `createMockToolCall(toolName, args, result?)` | Creates a tool-call shape using `mockId()` |
| `createMockStepResult(options?)` | Produces a full `StepResult` with all required fields filled |
| `collectStream(stream)` | Drains an `AsyncIterable<T>` to `T[]` |
| `collectTextStream(stream)` | Drains a text stream to a single string |
| `createMockStreamTextResult(overrides?)` | Builds a mock `StreamTextResult` |
| `createMockGenerateTextResult(overrides?)` | Builds a mock `GenerateTextResult` |
| `mockAISDKFunctions()` | Returns `vi.fn()` stubs for all four AI SDK generation functions |
| `waitFor(condition, timeout, interval)` | Polls until a condition resolves true (useful for async side effects) |
| `createAutoAbortController(delay)` | AbortController that auto-aborts after a delay |
| `convertArrayToReadableStream(array)` | Wraps a plain array in a `ReadableStream` |
| `convertArrayToAsyncIterable(array)` | Wraps a plain array in an `AsyncIterable` |

### packages/core/src/agent/subagent/test-utils.ts

Focused on multi-agent setups:

| Function | Purpose |
|---|---|
| `createMockAgent(options?)` | Creates a real `Agent` with a mock model; all agent config fields supported |
| `createMockAgentWithStubs(options?)` | Real agent + `vi.spyOn` stubs on all four generation methods |
| `createTestMessage(content, role?)` | Creates a `UIMessage` with proper `parts` format |
| `createTestMessages(...contents)` | Batch message creation |
| `mockStreamEvents` | Named helpers for building stream event shapes |
| `createMockStream(events)` | Async generator producing test stream events |
| `collectStream(stream)` | Drains an async iterable |
| `createMockTool(name?)` / `createMockToolkit(name?)` | Tool and toolkit factories |
| `subAgentFixtures` | Pre-wired agent/method/schema configurations |

### packages/core/src/memory/test-utils.ts

Storage adapter test helpers:

| Function | Purpose |
|---|---|
| `createTestUIMessage(overrides?)` | `UIMessage` with auto-generated ID |
| `createTestMessages(count, role?)` | Alternating user/assistant messages |
| `createTestConversation(overrides?)` | `CreateConversationInput` with auto-generated ID |
| `createTestConversations(count)` | Batch conversation creation |
| `extractMessageText(message)` | Pulls text from `UIMessage.parts` |
| `assertConversationsEqual(actual, expected)` | Deep-field comparison ignoring timestamp precision |
| `assertMessagesEqual(actual, expected)` | Array-level message comparison using `safeStringify` |

### packages/core/src/test-utils/mocks/workflows.ts

Workflow testing helpers:

| Function | Purpose |
|---|---|
| `createMockWorkflowExecuteContext(overrides?)` | Produces a `WorkflowExecuteContext` with vi.fn() stubs for `suspend`, `bail`, `abort`, logger, and writer |

## CI & Coverage

### CI Pipeline (GitHub Actions)

The pipeline has three test phases that must all pass before a release is permitted:

**Phase 1 — Unit/Integration (matrix)**

Packages tested in matrix: `cli`, `core` (and additional scopes defined in the matrix). Each package builds with all its dependencies before running its own tests:

```yaml
- name: Build Package and Dependencies
  run: lerna run build --scope "${{ steps.scope.outputs.scope }}" --include-dependencies
- name: Test Package
  run: lerna run test --scope "${{ steps.scope.outputs.scope }}"
```

**Phase 2 — E2E Tests**

The `packages/e2e` suite runs with a Postgres service container (v16) for real persistence tests. LibSQL tests run in-process.

**Phase 3 — Prerelease gate**

Runs both PostgreSQL integration tests and type-compatibility checks. Includes Node.js version matrix (20, 22, 24) for compatibility verification.

### Coverage Configuration

Coverage is collected per-package, not monorepo-wide. Source includes `src/**/*.ts`, excludes `*.d.ts` and barrel `index.ts` files. Reporters: text (terminal), JSON, HTML.

No minimum coverage threshold is enforced in the Vitest config at time of research. Coverage is collected on demand via `pnpm test:all:coverage`.

## Common Gotchas

### 1. Never use JSON.stringify — use safeStringify

The codebase-wide rule from `CLAUDE.md` applies everywhere including tests. Import from `@voltagent/internal`:

```typescript
import { safeStringify } from "@voltagent/internal";
// Use safeStringify(obj) instead of JSON.stringify(obj)
```

The `safe-stringify.spec.ts` exhaustively tests circular reference scenarios — it is a good reference for understanding why this rule exists.

### 2. MockLanguageModelV3 usage shape changed in ai v4

The provider-internal usage shape is **not** the SDK-public `LanguageModelUsage`. Use the nested form:

```typescript
// CORRECT (provider shape inside doGenerate/doStream)
usage: {
  inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: 5, text: 5, reasoning: 0 },
}

// WRONG (old SDK-public shape — will cause type errors or runtime mismatches)
usage: {
  promptTokens: 10,
  completionTokens: 5,
  totalTokens: 15,
}
```

The `createMockLanguageModel()` utility in `agent/test-utils.ts` normalizes between these shapes automatically.

### 3. vi.mock hoisting — always use vi.importActual for partial mocks

When partially mocking `"ai"`, always re-spread the actual module. Forgetting this strips `convertToCoreMessages` and related converters, causing silent failures in message normalization:

```typescript
vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return { ...actual, generateText: vi.fn() }; // keep converters
});
```

### 4. afterEach cleanup is required

Agent tests must call `vi.clearAllMocks()` in both `beforeEach` and `afterEach`. Agent instances register themselves with the `AgentRegistry` singleton; leaking them between tests produces state pollution:

```typescript
afterEach(() => {
  vi.clearAllMocks();
  // If testing registry behavior, also reset: AgentRegistry.getInstance().clear()
});
```

### 5. Test file placement mirrors source structure

A test file at `src/agent/subagent/bail.spec.ts` tests `src/agent/subagent/bail.ts`. Do not place tests in a top-level `__tests__` directory (the `rag` package is an outlier; the canonical pattern used in `core` is co-location).

### 6. Integration specs vs unit specs are distinguishable by filename

The `.integration.spec.ts` naming convention signals that the test wires multiple real collaborators. The `vitest.config.mts` includes both via `"**/*.spec.ts"` — there is no separate include path for integration tests.

### 7. The e2e package requires external services

`packages/e2e` tests fail without a running Postgres instance. Do not run `pnpm test:all` from a cold local environment without first checking whether e2e is scoped out. The root `test:all` script scopes to `@voltagent/*` which includes `@voltagent/e2e`.

### 8. Type tests require a separate typecheck pass

Type tests (`.spec-d.ts`) run via Vitest's `typecheck` mode, not the standard test runner. The config separates them:

```typescript
typecheck: {
  include: ["**/**/*.spec-d.ts"],
  exclude: ["**/**/*.spec.ts"],
},
```

Running `pnpm vitest run` without `--typecheck` skips all `.spec-d.ts` files silently.

### 9. Workflow step tests use createMockWorkflowExecuteContext

Every `andAgent`, `andAll`, `andMap`, etc. step spec passes a mock context produced by `createMockWorkflowExecuteContext()`. Do not hand-construct a context object — it has non-trivial shape requirements (`setWorkflowState` mutation logic, `suspend`/`bail`/`abort` error contracts).

### 10. Stream utilities are not interchangeable

`convertArrayToReadableStream` produces a `ReadableStream`; `convertArrayToAsyncIterable` produces an `AsyncIterable`. The agent streaming API accepts both in different positions. Using the wrong one produces silent type errors or runtime hangs when the consumer expects `.getReader()` on an async iterable.
