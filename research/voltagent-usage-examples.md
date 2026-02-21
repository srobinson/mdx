---
title: VoltAgent Usage Examples and Patterns
date: 2026-03-13
tags: [voltagent, examples, getting-started, usage, frameworks, agents]
---

# VoltAgent Usage Examples and Patterns

Complete guide to building AI agents with VoltAgent, covering installation, basic patterns, advanced features, and real-world examples.

## Quick Start

### Minimal Working Example

Create a new VoltAgent project in seconds:

```bash
npm create voltagent-app@latest
```

This scaffolds a complete project with agents, workflows, and a dev server.

### Basic Agent Setup (5 lines of code)

```typescript
import { Agent, VoltAgent } from "@voltagent/core";
import { honoServer } from "@voltagent/server-hono";
import { createPinoLogger } from "@voltagent/logger";

const logger = createPinoLogger({ name: "my-agent" });

const agent = new Agent({
  name: "Assistant",
  instructions: "A helpful assistant that can check weather and help with various tasks",
  model: "openai/gpt-4o-mini",
  memory: new Memory({ storage: new LibSQLMemoryAdapter() }),
});

new VoltAgent({
  agents: { agent },
  server: honoServer(),
  logger,
});
```

Run it:
```bash
npm run dev
# Server starts at http://localhost:3141
```

## Example Catalog

VoltAgent includes 70+ production-ready examples demonstrating every feature. Here are the key categories:

### Foundation Examples

| Example | Purpose | Key Concepts |
|---------|---------|--------------|
| [base](./examples/base) | Minimal starter | Agent, Memory, LibSQL |
| [with-tools](./examples/with-tools) | Zod-typed tools | createTool, parameters, execute |
| [with-nextjs](./examples/with-nextjs) | React UI + streaming | API routes, streamText, streaming response |
| [with-workflow](./examples/with-workflow) | Multi-step automation | createWorkflow, andThen, andAgent, suspend/resume |

### Advanced Patterns

| Example | Purpose | Key Concepts |
|---------|---------|--------------|
| [with-subagents](./examples/with-subagents) | Multi-agent orchestration | Supervisor, subAgents, delegation |
| [with-rag-chatbot](./examples/with-rag-chatbot) | Retrieval-augmented generation | BaseRetriever, retrieve(), context injection |
| [with-mcp](./examples/with-mcp) | Model Context Protocol integration | MCPConfiguration, MCP tools |
| [with-middleware](./examples/with-middleware) | Request/response middleware | Input/output hooks, retry feedback |

### Provider & Service Integration

| Example | LLM Provider | Features |
|---------|--------------|----------|
| [with-anthropic](./examples/with-anthropic) | Claude | Anthropic API via AI SDK |
| [with-google-ai](./examples/with-google-ai) | Google Gemini | Google AI provider |
| [with-groq-ai](./examples/with-groq-ai) | Groq | Ultra-low latency LPU |
| [with-amazon-bedrock](./examples/with-amazon-bedrock) | AWS Bedrock | AWS model inference |

### Deployment & Infrastructure

| Example | Platform | Deployment |
|---------|----------|-----------|
| [with-cloudflare-workers](./examples/with-cloudflare-workers) | Cloudflare Workers | Serverless edge computing |
| [with-netlify-functions](./examples/with-netlify-functions) | Netlify | Serverless functions |
| [next-js-chatbot-starter-template](./examples/next-js-chatbot-starter-template) | Next.js | Full-stack React app |

### Feature Demonstrations

| Example | Feature | Implementation |
|---------|---------|-----------------|
| [with-vector-search](./examples/with-vector-search) | Semantic memory | Embeddings + vector recall |
| [with-resumable-streams](./examples/with-resumable-streams) | Persistent streaming | Redis-backed SSE storage |
| [with-guardrails](./examples/with-guardrails) | Output validation | Schema enforcement |
| [with-live-evals](./examples/with-live-evals) | Agent evaluation | Online assessment |
| [with-voice-openai](./examples/with-voice-openai) | Text-to-speech | OpenAI TTS integration |

### Real-World Examples

| Example | Use Case | Tech Stack |
|---------|----------|-----------|
| [with-whatsapp](./examples/with-whatsapp) | Food ordering chatbot | WhatsApp, Database, Conversations |
| [with-youtube-to-blog](./examples/with-youtube-to-blog) | Content generation | YouTube API, Markdown, Multi-agent |
| [with-ad-creator](./examples/with-ad-creator) | Instagram ad generator | BrowserBase, Google Gemini, Image generation |
| [with-recipe-generator](./examples/with-recipe-generator) | Recipe recommendations | Semantic matching, Preferences |
| [with-research-assistant](./examples/with-research-assistant) | Multi-agent research | Agent coordination, Report generation |

## Common Patterns

### Creating an Agent

**Simple agent with model only:**
```typescript
const agent = new Agent({
  name: "SimpleAssistant",
  instructions: "You are a helpful assistant",
  model: "openai/gpt-4o-mini",
});
```

**Agent with memory:**
```typescript
const memory = new Memory({
  storage: new LibSQLMemoryAdapter({ url: "file:./.voltagent/memory.db" }),
  embedding: "openai/text-embedding-3-small", // For semantic search
  vector: new LibSQLVectorAdapter(), // Vector storage
  generateTitle: true, // Auto-summarize conversations
});

const agent = new Agent({
  name: "ContextualAssistant",
  instructions: "Remember previous conversations",
  model: "openai/gpt-4o-mini",
  memory,
});
```

**Agent with purpose (for supervisor routing):**
```typescript
const agent = new Agent({
  name: "ContentCreator",
  purpose: "Drafts short content on requested topics", // Helps supervisor understand capability
  instructions: "You are a creative content writer",
  model: "openai/gpt-4o-mini",
});
```

### Adding Tools

**Basic tool with Zod schema:**
```typescript
import { createTool } from "@voltagent/core";
import { z } from "zod";

export const fetchRepoStarsTool = createTool({
  name: "repo_stars",
  description: "Fetches the number of stars for a GitHub repository",
  parameters: z.object({
    owner: z.string().describe("Repository owner"),
    repo: z.string().describe("Repository name"),
  }),
  execute: async ({ owner, repo }) => {
    try {
      const response = await octokit.repos.get({ owner, repo });
      return {
        success: true,
        stars: response.data.stargazers_count,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  },
});

// Attach to agent
const agent = new Agent({
  name: "RepoAnalyzer",
  tools: [fetchRepoStarsTool],
  // ... other config
});
```

**Tool with streaming support:**
```typescript
const streamingTool = createTool({
  name: "stream_processor",
  description: "Processes data with streaming output",
  parameters: z.object({
    input: z.string(),
  }),
  execute: async ({ input }, observationCollector) => {
    // Use observationCollector to emit stream events
    if (observationCollector) {
      observationCollector.collect({
        type: "log",
        data: "Processing started...",
      });
    }

    // Do work
    const result = await processLongOperation(input);

    if (observationCollector) {
      observationCollector.collect({
        type: "log",
        data: `Completed with ${result.length} items`,
      });
    }

    return { success: true, result };
  },
});
```

**Tool with cancellation support:**
```typescript
const cancellableTool = createTool({
  name: "long_operation",
  description: "Can be cancelled mid-execution",
  parameters: z.object({
    duration: z.number(),
  }),
  execute: async ({ duration }, observationCollector, signal) => {
    for (let i = 0; i < duration; i += 100) {
      if (signal?.aborted) {
        return { error: "Operation cancelled", cancelled: true };
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    return { success: true, duration };
  },
});
```

### Configuring Memory

**In-memory (development/testing):**
```typescript
import { InMemoryStorageAdapter } from "@voltagent/core";

const memory = new Memory({
  storage: new InMemoryStorageAdapter(),
  // Cleared on server restart
});
```

**Persistent with LibSQL:**
```typescript
import { LibSQLMemoryAdapter, LibSQLVectorAdapter } from "@voltagent/libsql";

const memory = new Memory({
  storage: new LibSQLMemoryAdapter({
    url: "file:./.voltagent/memory.db", // Local SQLite
    // OR: url: "libsql://api-key@db-name.turso.io" for Turso cloud
  }),
  embedding: "openai/text-embedding-3-small",
  vector: new LibSQLVectorAdapter(), // Semantic search
  generateTitle: true, // Auto-title conversations
});
```

**Working memory (per-conversation facts):**
```typescript
// Agent has built-in read/update tools for working memory
const agent = new Agent({
  name: "Agent",
  instructions: `You have access to working memory tools:
    - read_working_memory: Get important facts from current conversation
    - update_working_memory: Store facts for future use
  Use these to track user preferences, context, etc.`,
  model: "openai/gpt-4o-mini",
  workingMemory: {
    enabled: true, // Enables memory tools
  },
});
```

### Multi-Agent Setup (Supervisor + Sub-agents)

**Supervisor delegating to specialists:**
```typescript
// Define specialist agents
const contentCreatorAgent = new Agent({
  name: "ContentCreator",
  purpose: "Writes engaging content",
  instructions: "You are a creative writer",
  model: "openai/gpt-4o-mini",
});

const formatterAgent = new Agent({
  name: "Formatter",
  purpose: "Formats and styles text",
  instructions: "You clean and format content",
  model: "openai/gpt-4o-mini",
  tools: [uppercaseTool, boldTool],
});

// Create supervisor that coordinates them
const supervisorAgent = new Agent({
  name: "Supervisor",
  instructions: "Coordinate content creation and formatting tasks",
  model: "openai/gpt-4o-mini",
  subAgents: [contentCreatorAgent, formatterAgent],
  supervisorConfig: {
    fullStreamEventForwarding: {
      types: ["tool-call", "tool-result", "text-delta"],
    },
  },
  memory,
});

// Initialize VoltAgent with all agents
new VoltAgent({
  agents: {
    supervisorAgent,
    contentCreatorAgent,
    formatterAgent,
  },
  logger,
  server: honoServer(),
});
```

**How supervisor routing works:**
1. Supervisor receives user message
2. Determines which sub-agent(s) can help based on their `purpose`
3. Delegates task to appropriate agent(s)
4. Collects responses and synthesizes answer
5. Returns unified response to user

### Streaming Responses

**In Next.js API route:**
```typescript
import { supervisorAgent } from "@/voltagent";
import { setWaitUntil } from "@voltagent/core";
import { after } from "next/server";

export async function POST(req: Request) {
  const { messages, conversationId = "default", userId = "user-1" } = await req.json();

  // Enable non-blocking telemetry export (for serverless)
  setWaitUntil(after);

  // Stream text from agent
  const result = await supervisorAgent.streamText(messages, {
    userId,
    conversationId,
  });

  // Return proper stream response for UI consumption
  return result.toUIMessageStreamResponse();
}
```

**Handling tool calls in streaming:**
```typescript
// The result includes tool execution during streaming
// Tool calls appear as message deltas in the stream
// UI can render:
// - text-delta: partial text responses
// - tool-call: when agent invokes a tool
// - tool-result: tool execution result
// - function-call: for compatibility
```

**Client-side streaming (React):**
```typescript
async function chat(messages: Message[]) {
  const response = await fetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });

  // Process streaming response
  for await (const chunk of response.body) {
    const decoded = new TextDecoder().decode(chunk);
    // Handle streamed content (tool calls, text deltas, etc.)
  }
}
```

### Retrievers for RAG

**Simple retriever implementation:**
```typescript
import { BaseRetriever, type BaseMessage } from "@voltagent/core";

class KnowledgeBaseRetriever extends BaseRetriever {
  private documents = [
    { id: "doc1", content: "VoltAgent is a TypeScript framework..." },
    { id: "doc2", content: "RAG stands for Retrieval-Augmented Generation..." },
  ];

  async retrieve(input: string | BaseMessage[]): Promise<string> {
    const query = typeof input === "string" ? input : (input[input.length - 1].content as string);
    const queryLower = query.toLowerCase();

    // Find relevant documents
    const relevantDocs = this.documents.filter((doc) =>
      doc.content.toLowerCase().includes(queryLower)
    );

    if (relevantDocs.length > 0) {
      return `Relevant Information:\n${relevantDocs.map((d) => `- ${d.content}`).join("\n")}`;
    }

    return "No relevant information found.";
  }
}

// Attach to agent
const agent = new Agent({
  name: "RAG Chatbot",
  instructions: "Answer based on knowledge base context",
  model: "openai/gpt-4o-mini",
  retriever: new KnowledgeBaseRetriever(), // Automatically injected into prompts
  memory,
});
```

**Vector-based retriever (with embeddings):**
```typescript
class VectorRetriever extends BaseRetriever {
  async retrieve(input: string | BaseMessage[]): Promise<string> {
    const query = typeof input === "string" ? input : input[input.length - 1].content;

    // Embed the query
    const queryEmbedding = await embedModel.embed({ text: query });

    // Find similar documents in vector DB
    const results = await vectorDB.search(queryEmbedding, { limit: 5 });

    // Return formatted context
    return results.map((r) => r.content).join("\n\n");
  }
}
```

**Automatic retriever invocation:**
```typescript
// Agent with retriever automatically:
// 1. Injects retrieved context into system prompt
// 2. Grounding responses in knowledge base
// 3. Improves accuracy with company-specific data
// 4. Supports citations (if retriever returns document IDs)
```

## Provider Examples

### OpenAI (GPT-4o, GPT-4, GPT-3.5)

```typescript
import { openai } from "@ai-sdk/openai";

const agent = new Agent({
  name: "OpenAI Agent",
  model: openai("gpt-4o"),
  // or: openai("gpt-4"), openai("gpt-3.5-turbo")
  instructions: "You are helpful.",
  memory,
});
```

### Anthropic (Claude 3.5 Sonnet/Opus/Haiku)

```typescript
import { anthropic } from "@ai-sdk/anthropic";

const agent = new Agent({
  name: "Claude Agent",
  model: anthropic("claude-3-5-sonnet-20241022"),
  // or: claude-3-opus-20240229, claude-3-haiku-20240307
  instructions: "You are thoughtful.",
  memory,
});
```

### Google (Gemini Pro/Flash)

```typescript
import { google } from "@ai-sdk/google";

const agent = new Agent({
  name: "Gemini Agent",
  model: google("gemini-2.0-flash"),
  // or: gemini-pro, gemini-pro-vision
  instructions: "You are creative.",
  memory,
});
```

### Groq (Ultra-fast inference)

```typescript
import { createLanguageModel } from "@ai-sdk/generic";

const agent = new Agent({
  name: "Groq Agent",
  model: createLanguageModel({
    apiId: "groq",
    provider: "https://api.groq.com/openai/v1",
    defaultObjectGenerationMode: "tool",
  }),
  instructions: "You respond quickly.",
  memory,
});
```

### AWS Bedrock

```typescript
import { bedrock } from "@ai-sdk/aws-bedrock";

const agent = new Agent({
  name: "Bedrock Agent",
  model: bedrock("anthropic.claude-3-5-sonnet-20241022-v2:0"),
  instructions: "You are enterprise-grade.",
  memory,
});
```

### Dynamic Provider Selection

```typescript
function getAIModel() {
  const provider = process.env.AI_PROVIDER || "openai";

  switch (provider) {
    case "anthropic":
      return anthropic("claude-3-5-sonnet-20241022");
    case "google":
      return google("gemini-2.0-flash");
    case "groq":
      return groq("mixtral-8x7b-32768");
    default:
      return openai("gpt-4o-mini");
  }
}

const agent = new Agent({
  name: "Flexible Agent",
  model: getAIModel(), // Swap provider via env var
  instructions: "You adapt to any model.",
  memory,
});
```

## Advanced Patterns

### Workflows with Human-in-the-Loop

**Suspend/resume pattern for approvals:**
```typescript
import { createWorkflow } from "@voltagent/core";

const expenseApprovalWorkflow = createWorkflow(
  {
    id: "expense-approval",
    input: z.object({
      employeeId: z.string(),
      amount: z.number(),
    }),
    result: z.object({
      status: z.enum(["approved", "rejected"]),
      approvedBy: z.string(),
    }),
  },
  andThen({
    id: "check-approval-needed",
    resumeSchema: z.object({
      approved: z.boolean(),
      managerId: z.string(),
    }),
    execute: async ({ data, suspend, resumeData }) => {
      // If resuming with manager's decision
      if (resumeData) {
        return { ...data, approved: resumeData.approved, approvedBy: resumeData.managerId };
      }

      // Check if approval needed
      if (data.amount > 500) {
        // Suspend workflow, waiting for manager input
        await suspend("Manager approval required", {
          employeeId: data.employeeId,
          amount: data.amount,
        });
      }

      // Auto-approve small expenses
      return { ...data, approved: true, approvedBy: "system" };
    },
  }),
  andThen({
    id: "process-decision",
    execute: async ({ data }) => ({
      status: data.approved ? "approved" : "rejected",
      approvedBy: data.approvedBy,
    }),
  })
);
```

### Workflow Control Flow

**Conditional branching:**
```typescript
andBranch({
  id: "categorize-order",
  branches: [
    {
      condition: ({ data }) => data.amount > 1000,
      step: andThen({
        id: "premium-handling",
        execute: async ({ data }) => ({ ...data, priority: "high" }),
      }),
    },
    {
      condition: ({ data }) => data.amount <= 1000,
      step: andThen({
        id: "standard-handling",
        execute: async ({ data }) => ({ ...data, priority: "normal" }),
      }),
    },
  ],
})
```

**Loops:**
```typescript
// Do-while: run at least once, then check condition
andDoWhile({
  id: "warmup-loop",
  step: andThen({
    id: "increment",
    execute: async ({ data }) => ({ ...data, counter: data.counter + 1 }),
  }),
  condition: ({ data }) => data.counter < 5,
})

// Do-until: run until condition is true
andDoUntil({
  id: "retry-loop",
  step: andThen({
    id: "retry",
    execute: async ({ data }) => await retryOperation(data),
  }),
  condition: ({ data }) => data.success === true,
})

// For-each: process array items
andForEach({
  id: "process-items",
  step: andThen({
    id: "transform-item",
    execute: async ({ data }) => data.toUpperCase(),
  }),
  concurrency: 3, // Process 3 at a time
})
```

**Agent steps in workflows:**
```typescript
andAgent(
  async ({ data }) => `
    Analyze this order for fraud:
    Order ID: ${data.orderId}
    Amount: $${data.amount}
    Items: ${data.items.join(", ")}

    Provide risk level (low/medium/high).
  `,
  analysisAgent,
  {
    schema: z.object({
      riskLevel: z.enum(["low", "medium", "high"]),
      reasoning: z.string(),
    }),
  }
)
```

### Custom Memory Adapters

**Building a custom storage adapter:**
```typescript
import { StorageAdapter } from "@voltagent/core";

class PostgresMemoryAdapter implements StorageAdapter {
  async save(key: string, value: string): Promise<void> {
    await pool.query(
      "INSERT INTO memory (key, value, created_at) VALUES ($1, $2, NOW())",
      [key, value]
    );
  }

  async retrieve(key: string): Promise<string | null> {
    const result = await pool.query("SELECT value FROM memory WHERE key = $1", [key]);
    return result.rows[0]?.value || null;
  }

  async retrieveAll(): Promise<Record<string, string>> {
    const result = await pool.query("SELECT key, value FROM memory");
    return Object.fromEntries(result.rows.map((r) => [r.key, r.value]));
  }

  async delete(key: string): Promise<void> {
    await pool.query("DELETE FROM memory WHERE key = $1", [key]);
  }
}

// Use custom adapter
const memory = new Memory({
  storage: new PostgresMemoryAdapter(),
});
```

### MCP Integration

**Using MCP tools in agents:**
```typescript
import { MCPConfiguration } from "@voltagent/core";
import path from "node:path";

const mcpConfig = new MCPConfiguration({
  servers: {
    filesystem: {
      type: "stdio",
      command: "npx",
      args: [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        path.resolve("./data"), // Safe directory
      ],
    },
    github: {
      type: "stdio",
      command: "npx",
      args: [
        "-y",
        "@modelcontextprotocol/server-github",
        process.env.GITHUB_TOKEN,
      ],
    },
  },
});

const agent = new Agent({
  name: "MCP Agent",
  instructions: "You can read files and interact with GitHub",
  model: "openai/gpt-4o-mini",
  tools: await mcpConfig.getTools(), // MCP tools mixed with custom tools
  memory,
});
```

**Available MCP servers:**
- `@modelcontextprotocol/server-filesystem` - Read/write files
- `@modelcontextprotocol/server-github` - GitHub API access
- `@modelcontextprotocol/server-google-drive` - Drive file access
- `@modelcontextprotocol/server-postgres` - Database queries
- Plus 50+ community servers

### Guardrails for Safety

**Input validation guardrail:**
```typescript
import { createInputGuardrail } from "@voltagent/core";

const contentFilter = createInputGuardrail({
  name: "content-filter",
  handler: async ({ input }) => {
    const text = typeof input === "string" ? input : JSON.stringify(input);

    // Check for prohibited terms
    if (text.includes("malicious") || text.includes("hack")) {
      return {
        pass: false,
        action: "block",
      };
    }

    return { pass: true };
  },
});

const agent = new Agent({
  name: "Safe Agent",
  model: "openai/gpt-4o-mini",
  instructions: "Be helpful and safe.",
  inputGuardrails: [contentFilter],
  memory,
});
```

**Output validation guardrail:**
```typescript
import { createOutputGuardrail } from "@voltagent/core";

const outputValidator = createOutputGuardrail<string>({
  name: "json-validator",
  handler: async ({ output }) => {
    try {
      JSON.parse(output);
      return { pass: true };
    } catch {
      return {
        pass: false,
        action: "block",
      };
    }
  },
});

const agent = new Agent({
  name: "JSON Agent",
  model: "openai/gpt-4o-mini",
  instructions: "Always return valid JSON",
  outputGuardrails: [outputValidator],
  memory,
});
```

### Observability & Tracing

**Enable OpenTelemetry tracing:**
```typescript
import { VoltAgentObservability } from "@voltagent/core";
import { LibSQLObservabilityAdapter } from "@voltagent/libsql";

new VoltAgent({
  agents: { agent },
  logger,
  server: honoServer(),
  observability: new VoltAgentObservability({
    storage: new LibSQLObservabilityAdapter(), // Store traces locally
    // OR: send to external service
    // exporter: new OTelExporter({ endpoint: "..." })
  }),
});

// Access traces via:
// - VoltOps Console (https://console.voltagent.dev)
// - Custom export endpoints
```

**Manual span creation:**
```typescript
import { createSpan } from "@voltagent/core";

const result = await createSpan({
  name: "custom-operation",
  attributes: { userId, operation: "payment" },
  async fn() {
    // Your code here
    return await processPayment();
  },
});
```

## Installation & Setup by Framework

### Standalone Node.js Project

```bash
mkdir my-agent
cd my-agent

# Initialize
npm init -y
npm install \
  @voltagent/core \
  @voltagent/server-hono \
  @voltagent/logger \
  @ai-sdk/openai \
  ai \
  zod \
  hono

# Optional: persistent memory
npm install @voltagent/libsql

# Create src/index.ts with agent code

# Add scripts to package.json
{
  "scripts": {
    "dev": "tsx watch --env-file=.env ./src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  }
}

# Run
npm run dev
```

### Next.js Integration

```bash
# Create Next.js app
npx create-next-app@latest my-agent --typescript

# Add VoltAgent dependencies
npm install \
  @voltagent/core \
  @voltagent/logger \
  @ai-sdk/openai \
  ai \
  zod

# Optional: persistent memory
npm install @voltagent/libsql

# Create lib/voltagent/agent.ts with agent definition
# Create app/api/chat/route.ts with POST handler
# Create app/page.tsx with UI
```

### Cloudflare Workers Deployment

```bash
# Create worker
npm create cloudflare@latest my-agent -- --type "hello-world"

# Add VoltAgent
npm install \
  @voltagent/core \
  @voltagent/server-hono \
  @ai-sdk/openai \
  ai \
  zod \
  hono

# src/index.ts uses honoServer adapter
# Deploy: npm run deploy
```

### Using the CLI

```bash
# Create new VoltAgent project with all scaffolding
npm create voltagent-app@latest

# Start dev server
npm run dev

# Deploy to VoltOps
npm run volt deploy
```

## Configuration Reference

### Agent Options

```typescript
new Agent({
  // Required
  name: string;
  model: string | LanguageModel;
  instructions: string;

  // Optional
  tools?: Tool[];
  subAgents?: Agent[];
  retriever?: BaseRetriever;
  memory?: Memory;
  purpose?: string; // For supervisor routing
  workingMemory?: { enabled: boolean };
  supervisorConfig?: {
    fullStreamEventForwarding?: {
      types: string[];
    };
  };
  inputGuardrails?: Guardrail[];
  outputGuardrails?: Guardrail[];
})
```

### Memory Options

```typescript
new Memory({
  storage: StorageAdapter; // Where conversations are stored
  embedding?: string; // "openai/text-embedding-3-small" for semantic search
  vector?: VectorAdapter; // Where embeddings are stored
  generateTitle?: boolean; // Auto-generate conversation titles
  maxMemoryItems?: number; // Limit stored conversations
})
```

### VoltAgent Server Options

```typescript
honoServer({
  port?: number; // Default: 3141
  hostname?: string;
  trustProxy?: boolean;
  // Custom endpoints
  onServer?: (server: Hono) => void;
})
```

## Common Tasks

### Testing Locally

```bash
# Start dev server
npm run dev

# Open VoltOps Console
# https://console.voltagent.dev

# Or test via curl
curl -X POST http://localhost:3141/agents/my-agent/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### Deploying to Production

**VoltOps Deployment (recommended):**
```bash
# Push to GitHub
git push origin main

# Deploy via console
# https://console.voltagent.dev/deployments

# Or CLI
npm run volt deploy
```

**Custom hosting:**
```bash
# Build project
npm run build

# Deploy dist/ folder to any Node.js host
# Environment variables:
# - OPENAI_API_KEY
# - DATABASE_URL (if using Postgres)
# - etc.

# Start with:
npm run start
```

### Managing Secrets

```bash
# Create .env file (never commit)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://...

# Load in code
import { config } from "dotenv";
config();

const model = openai(process.env.OPENAI_API_KEY);
```

### Working with Different Models

```typescript
// Swap models easily
const gpt4 = openai("gpt-4o");
const claude = anthropic("claude-3-5-sonnet-20241022");
const gemini = google("gemini-2.0-flash");

const agent = new Agent({
  model: gpt4, // Change here
  // ... rest of config
});
```

## Debugging & Troubleshooting

### Enable Debug Logging

```typescript
import { createPinoLogger } from "@voltagent/logger";

const logger = createPinoLogger({
  name: "my-agent",
  level: "debug", // Show all logs
});
```

### Check Memory Issues

```typescript
// Inspect conversation history
const conversations = await memory.storage.retrieveAll();
console.log("Conversations:", conversations);

// Clear memory if needed
await memory.storage.delete("conversation-key");
```

### Tool Execution Issues

```typescript
// Tools return result objects with success status
const toolResult = await myTool.execute({ input });
if (toolResult.success === false) {
  console.error("Tool failed:", toolResult.error);
}
```

## Best Practices

1. **Type everything:** Use Zod for tool parameters and workflow schemas
2. **Use memory:** Store context across conversations for better responses
3. **Add guardrails:** Validate inputs and outputs for safety
4. **Log extensively:** Use logger for debugging production issues
5. **Test workflows locally:** VoltOps console makes testing easy
6. **Version tools:** Include tool version in metadata
7. **Handle errors gracefully:** Always return status in tool results
8. **Use retrievers for context:** Ground responses in company data
9. **Monitor costs:** Different models have different pricing
10. **Start simple:** Build minimal agent first, add features incrementally

## Next Steps

- Explore [VoltAgent documentation](https://voltagent.dev/docs/)
- Try the [interactive tutorial](https://voltagent.dev/tutorial/introduction/)
- Join [Discord community](https://discord.gg/VoltAgent)
- Watch [tutorial videos](https://www.youtube.com/c/VoltAgent)
- Deploy your first agent to [VoltOps](https://console.voltagent.dev)
