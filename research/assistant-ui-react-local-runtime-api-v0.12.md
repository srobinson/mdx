---
title: "@assistant-ui/react LocalRuntime API - v0.12 (no Vercel AI SDK)"
type: research
tags: [assistant-ui, react, chat-ui, local-runtime, sse, streaming, typescript]
summary: Complete API for building a custom chat UI with @assistant-ui/react using LocalRuntime and a custom SSE backend, without Vercel AI SDK.
status: active
source: quick-research
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

`@assistant-ui/react` v0.12.17 provides `useLocalRuntime` + `AssistantRuntimeProvider` as the primary path for a custom backend. You implement one interface (`ChatModelAdapter`) and get full state management, streaming, cancellation, and UI primitives. No Vercel AI SDK dependency.

## Package Versions (as of 2026-03-11)

| Package | Version |
|---------|---------|
| `@assistant-ui/react` | 0.12.17 |
| `@assistant-ui/react-streamdown` | 0.1.5 |
| `@streamdown/code` | 1.1.0 |
| `@streamdown/react` | does not exist on npm (use `streamdown` directly) |

Install:
```bash
npm install @assistant-ui/react @assistant-ui/react-streamdown streamdown @streamdown/code
```

---

## 1. ChatModelAdapter - The Core Interface

Source: `@assistant-ui/core` -> `dist/runtime/utils/chat-model-adapter.d.ts`

```typescript
type ChatModelAdapter = {
  run(options: ChatModelRunOptions): Promise<ChatModelRunResult> | AsyncGenerator<ChatModelRunResult, void>;
};

type ChatModelRunOptions = {
  readonly messages: readonly ThreadMessage[];   // full conversation history
  readonly runConfig: RunConfig;
  readonly abortSignal: AbortSignal;             // pass to fetch() for cancellation
  readonly context: ModelContext;                // tool definitions etc.
  readonly config: ModelContext;                 // @deprecated alias for context
  readonly unstable_assistantMessageId?: string;
  readonly unstable_threadId?: string;
  readonly unstable_parentId?: string | null;
  unstable_getMessage(): ThreadMessage;          // live access to current message state
};

type ChatModelRunResult = {
  readonly content?: readonly ThreadAssistantMessagePart[] | undefined;
  readonly status?: MessageStatus | undefined;
  readonly metadata?: {
    readonly unstable_state?: ReadonlyJSONValue;
    readonly unstable_annotations?: readonly ReadonlyJSONValue[] | undefined;
    readonly unstable_data?: readonly ReadonlyJSONValue[] | undefined;
    readonly steps?: readonly ThreadStep[] | undefined;
    readonly timing?: MessageTiming | undefined;
    readonly custom?: Record<string, unknown> | undefined;
  };
};

// Content part types:
// { type: "text"; text: string }
// { type: "reasoning"; text: string }
// { type: "tool-call"; toolCallId: string; toolName: string; args: object; result?: any }
// { type: "image"; image: string }
// { type: "source"; ... }
```

### Non-streaming adapter (simple fetch):

```typescript
const myAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal: abortSignal,
    });
    const data = await res.json();
    return { content: [{ type: "text", text: data.text }] };
  },
};
```

### Streaming adapter (SSE / custom backend):

Use `async *run` (generator syntax). Yield partial results as chunks arrive. The yielded `content` is always the **full accumulated** text, not a delta.

```typescript
const mySSEAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal: abortSignal,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let accumulated = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });

      // Parse SSE lines
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data);
            // Adjust field name to match your backend's SSE payload
            const delta = parsed.delta ?? parsed.text ?? "";
            accumulated += delta;
            yield { content: [{ type: "text", text: accumulated }] };
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  },
};
```

---

## 2. useLocalRuntime + AssistantRuntimeProvider

Source: `@assistant-ui/core/react` -> `runtimes/useLocalRuntime.d.ts`

```typescript
const useLocalRuntime: (
  chatModel: ChatModelAdapter,
  options?: LocalRuntimeOptions
) => AssistantRuntime;

type LocalRuntimeOptions = {
  initialMessages?: readonly ThreadMessageLike[] | undefined;
  maxSteps?: number | undefined;               // default 5 - max sequential tool calls
  cloud?: AssistantCloud | undefined;          // AssistantCloud for multi-thread persistence
  adapters?: {
    history?: ThreadHistoryAdapter;
    attachments?: AttachmentAdapter;
    speech?: SpeechSynthesisAdapter;
    dictation?: DictationAdapter;
    feedback?: FeedbackAdapter;
    suggestion?: SuggestionAdapter;
  } | undefined;
  unstable_humanToolNames?: string[] | undefined;
};
```

### Provider setup:

```typescript
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const myAdapter: ChatModelAdapter = { async *run(...) { /* ... */ } };

export function MyRuntimeProvider({ children }: { children: React.ReactNode }) {
  const runtime = useLocalRuntime(myAdapter);
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
```

`AssistantRuntimeProvider` props:
```typescript
{
  runtime: AssistantRuntime;   // required
  aui?: AssistantClient | null;
  children: ReactNode;
}
```

---

## 3. Thread Primitives

Imported as `import { ThreadPrimitive } from "@assistant-ui/react"`.

### ThreadPrimitive.Root

Renders a `<div>`. Accepts all div props + `asChild`.

### ThreadPrimitive.Viewport

Scrollable message area. Key props:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `autoScroll` | boolean | true (bottom) / false (top) | Auto-scroll to bottom on new messages |
| `turnAnchor` | `"top" \| "bottom"` | `"bottom"` | Classic chat = bottom; focused reading = top |
| `scrollToBottomOnRunStart` | boolean | true | Scroll when generation starts |
| `scrollToBottomOnInitialize` | boolean | true | Scroll on first load |
| `scrollToBottomOnThreadSwitch` | boolean | true | Scroll when switching threads |

### ThreadPrimitive.Messages

Required `components` prop (two valid shapes):

```typescript
// Shape 1: single catch-all
{ Message: ComponentType }

// Shape 2: role-specific
{
  UserMessage: ComponentType;
  AssistantMessage: ComponentType;
  SystemMessage?: ComponentType;
  EditComposer?: ComponentType;         // editing any message
  UserEditComposer?: ComponentType;
  AssistantEditComposer?: ComponentType;
  SystemEditComposer?: ComponentType;
}
```

### ThreadPrimitive.ScrollToBottom

Renders a `<button>`. Disabled when already at bottom. Props: `asChild`, `behavior?: ScrollBehavior`.

### ThreadPrimitive.ViewportFooter

Measures its height for scroll offset calculations. Use with `className="sticky bottom-0"` to keep composer pinned at bottom.

### ThreadPrimitive.Empty / ThreadPrimitive.If

`ThreadPrimitive.Empty` renders children only when no messages. `ThreadPrimitive.If` is deprecated - use `<AuiIf condition={(s) => ...} />`.

### Minimal Thread layout:

```tsx
import { ThreadPrimitive, ComposerPrimitive } from "@assistant-ui/react";

function MyThread() {
  return (
    <ThreadPrimitive.Root className="flex flex-col h-full">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto p-4">
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMsg,
            AssistantMessage: AssistantMsg,
          }}
        />
        <ThreadPrimitive.ViewportFooter className="sticky bottom-0 bg-white">
          <MyComposer />
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
}
```

---

## 4. Composer Primitives

```typescript
import { ComposerPrimitive } from "@assistant-ui/react";
```

| Component | Renders | Notes |
|-----------|---------|-------|
| `ComposerPrimitive.Root` | `<form>` | Intercepts submit, calls send |
| `ComposerPrimitive.Input` | `<textarea>` (auto-resize) | See props below |
| `ComposerPrimitive.Send` | `<button>` | Disabled when empty or running |
| `ComposerPrimitive.Cancel` | `<button>` | Disabled when not running |
| `ComposerPrimitive.AddAttachment` | `<button>` | Requires AttachmentAdapter |
| `ComposerPrimitive.Attachments` | renders attachment list | |
| `ComposerPrimitive.AttachmentDropzone` | `<div>` | Drag-and-drop area |
| `ComposerPrimitive.If` | conditional render | e.g. `<ComposerPrimitive.If running>` |

### ComposerPrimitive.Input props:

```typescript
{
  asChild?: boolean;
  cancelOnEscape?: boolean;              // default true
  submitMode?: "enter" | "ctrlEnter" | "none";  // default "enter"
  unstable_focusOnRunStart?: boolean;    // default true
  unstable_focusOnScrollToBottom?: boolean;  // default true
  unstable_focusOnThreadSwitched?: boolean;  // default true
  addAttachmentOnPaste?: boolean;        // default true - paste files as attachments
  // plus all textarea props (placeholder, disabled, className, ...)
}
```

### Simple Composer:

```tsx
function MyComposer() {
  return (
    <ComposerPrimitive.Root className="flex gap-2 p-2 border-t">
      <ComposerPrimitive.Input
        placeholder="Send a message..."
        className="flex-1 resize-none border rounded p-2"
        submitMode="enter"
      />
      <ComposerPrimitive.Cancel className="px-3 py-2 bg-red-500 text-white rounded">
        Stop
      </ComposerPrimitive.Cancel>
      <ComposerPrimitive.Send className="px-3 py-2 bg-blue-500 text-white rounded">
        Send
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}
```

---

## 5. Message Part Rendering

For the `AssistantMessage` component passed to `ThreadPrimitive.Messages`:

```typescript
import { MessagePrimitive, MessagePartPrimitive } from "@assistant-ui/react";
```

### MessagePrimitive.Parts (MessagePrimitive.Content)

Renders all parts of a message with the given component map:

```typescript
<MessagePrimitive.Parts
  components={{
    Text: MyTextPart,         // TextMessagePartComponent
    Image: MyImagePart,
    Reasoning: MyReasoning,
    Source: MySource,
    File: MyFilePart,
    Empty: MyEmpty,
    tools: {
      by_name: { myTool: MyToolComponent },
      Fallback: DefaultToolComponent,
    },
  }}
/>
```

### MessagePartPrimitive.Text

Renders the text string from context. Props:
- `smooth?: boolean` (default true) - streaming animation
- `component?: ElementType` (default `"span"`)
- All other span props

### MessagePartPrimitive.InProgress

Renders children only while the part is still streaming.

### Typical AssistantMessage:

```tsx
function AssistantMsg() {
  return (
    <MessagePrimitive.Root className="flex gap-2 p-2">
      <MessagePrimitive.Parts
        components={{
          Text: ({ text }) => <p className="prose">{text}</p>,
          tools: { Fallback: ToolCallDisplay },
        }}
      />
    </MessagePrimitive.Root>
  );
}
```

---

## 6. @assistant-ui/react-streamdown Integration

Source: package README and dist/index.d.ts.

`StreamdownTextPrimitive` is a drop-in replacement for `MessagePartPrimitive.Text`. It reads the text part from the same message context - no extra wiring needed.

### Install:

```bash
npm install @assistant-ui/react-streamdown streamdown @streamdown/code
```

### Basic usage (inside a Text part component):

```tsx
import { StreamdownTextPrimitive } from "@assistant-ui/react-streamdown";

// Used as the Text component in MessagePrimitive.Parts
function AssistantTextPart() {
  return <StreamdownTextPrimitive className="prose" />;
}
```

### With code syntax highlighting:

```tsx
import { StreamdownTextPrimitive } from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { useMemo } from "react";

const plugins = { code }; // defined outside component or useMemo

function AssistantTextPart() {
  return (
    <StreamdownTextPrimitive
      plugins={plugins}
      shikiTheme={["github-light", "github-dark"]}
      className="prose"
    />
  );
}
```

### All StreamdownTextPrimitive props:

| Prop | Type | Description |
|------|------|-------------|
| `mode` | `"streaming" \| "static"` | Default: `"streaming"` - auto-detects from message state |
| `plugins` | `{ code?, math?, mermaid?, cjk? }` | Plugin config (pass by reference, not inline) |
| `shikiTheme` | `[string, string]` | Light/dark themes from Shiki (e.g. `["github-light", "github-dark"]`) |
| `components` | `{ SyntaxHighlighter?, CodeHeader? }` | Custom code block rendering |
| `componentsByLanguage` | `Record<string, { SyntaxHighlighter? }>` | Per-language overrides |
| `preprocess` | `(text: string) => string` | Text preprocessing before parsing |
| `controls` | `boolean \| object` | Code block copy/expand UI controls |
| `containerProps` | `object` | Props for the container `<div>` |
| `containerClassName` | `string` | Class name for container |
| `remarkRehypeOptions` | `object` | Passed to remark-rehype |
| `BlockComponent` | `ComponentType<{content, index}>` | Custom block renderer |
| `parseMarkdownIntoBlocksFn` | `(md: string) => string[]` | Custom block splitting |
| `remend` | `object` | Incomplete markdown auto-completion |
| `linkSafety` | `object` | Link safety confirmation modal config |
| `allowedTags` | `object` | HTML tag whitelist |

### Wire into messages:

```tsx
import { MessagePrimitive } from "@assistant-ui/react";
import { StreamdownTextPrimitive } from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { useMemo } from "react";

const plugins = { code };

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex gap-3 px-4 py-2">
      <div className="flex-1">
        <MessagePrimitive.Parts
          components={{
            Text: () => (
              <StreamdownTextPrimitive
                plugins={plugins}
                shikiTheme={["github-light", "github-dark"]}
                className="prose prose-sm max-w-none"
              />
            ),
          }}
        />
      </div>
    </MessagePrimitive.Root>
  );
}
```

---

## 7. Full Wiring Example (Custom SSE Backend)

```tsx
// runtime-provider.tsx
import { AssistantRuntimeProvider, useLocalRuntime } from "@assistant-ui/react";
import type { ChatModelAdapter } from "@assistant-ui/react";

// Matches your /api/chat SSE endpoint from ALP-1133
const amAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const res = await fetch("http://localhost:4000/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: messages.map((m) => ({
          role: m.role,
          content: m.content
            .filter((p) => p.type === "text")
            .map((p) => (p as any).text)
            .join(""),
        })),
      }),
      signal: abortSignal,
    });

    if (!res.ok) throw new Error(`Backend error: ${res.status}`);

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let text = "";
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      // Process complete SSE lines
      const lines = buf.split("\n");
      buf = lines.pop() ?? ""; // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;
        try {
          const evt = JSON.parse(payload);
          if (evt.delta) {
            text += evt.delta;
            yield { content: [{ type: "text", text }] };
          }
        } catch { /* skip */ }
      }
    }
  },
};

export function RuntimeProvider({ children }: { children: React.ReactNode }) {
  const runtime = useLocalRuntime(amAdapter);
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
```

```tsx
// chat.tsx - full composable UI
import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
} from "@assistant-ui/react";
import { StreamdownTextPrimitive } from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";

const plugins = { code };

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end px-4 py-2">
      <div className="max-w-[80%] bg-blue-500 text-white rounded-2xl px-4 py-2">
        <MessagePrimitive.Parts
          components={{ Text: ({ text }) => <span>{text}</span> }}
        />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex px-4 py-2">
      <div className="max-w-[80%]">
        <MessagePrimitive.Parts
          components={{
            Text: () => (
              <StreamdownTextPrimitive
                plugins={plugins}
                shikiTheme={["github-light", "github-dark"]}
                className="prose prose-sm max-w-none"
              />
            ),
          }}
        />
      </div>
    </MessagePrimitive.Root>
  );
}

function Composer() {
  return (
    <ComposerPrimitive.Root className="flex items-end gap-2 p-3 border-t bg-white">
      <ComposerPrimitive.Input
        placeholder="Ask anything..."
        className="flex-1 min-h-[40px] max-h-[200px] resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        submitMode="enter"
      />
      <ComposerPrimitive.Cancel className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded-lg disabled:opacity-50">
        Stop
      </ComposerPrimitive.Cancel>
      <ComposerPrimitive.Send className="px-3 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50">
        Send
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

export function Chat() {
  return (
    <ThreadPrimitive.Root className="flex flex-col h-full">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
        <ThreadPrimitive.Empty>
          <div className="flex items-center justify-center h-full text-gray-400">
            Start a conversation
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{ UserMessage, AssistantMessage }}
        />
        <ThreadPrimitive.ViewportFooter className="sticky bottom-0">
          <Composer />
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
}
```

---

## Key Notes

1. **`async *run` vs `async run`**: Use generator syntax for streaming. Plain `async run` works for non-streaming but will block the UI until the full response arrives.

2. **Yield accumulated content, not deltas**: Each `yield` must contain the full `text` built so far, not just the new chunk. The runtime diffs this internally.

3. **`abortSignal` propagation**: Always pass to `fetch()`. The runtime calls `controller.abort()` when the user clicks Cancel or navigates away.

4. **`StreamdownTextPrimitive` location**: Must be rendered inside a `MessagePrimitive.Parts` `Text` component - it reads from message part context via hooks.

5. **Plugin objects stability**: Pass `plugins` by stable reference (module-level or `useMemo`) to prevent re-renders on every keystroke.

6. **`@streamdown/react` does not exist**: The correct package is `streamdown` (the core) plus `@assistant-ui/react-streamdown` (the adapter). `@streamdown/code` provides code highlighting.

7. **v0.13 deprecation incoming**: `useAssistantRuntime`, `ThreadPrimitive.If`, `MessagePrimitive.If`, `AssistantIf` are deprecated. New API uses `useAui()` and `<AuiIf condition={(s) => s.thread.isEmpty} />`.

---

## Sources

- `npm pack @assistant-ui/react@0.12.17` - type declarations inspected directly
- `npm pack @assistant-ui/core@0.1.5` - core types (`ChatModelAdapter`, `useLocalRuntime`)
- `npm pack @assistant-ui/react-streamdown@0.1.5` - README and type declarations
- https://assistant-ui.com/docs/runtimes/pick-a-runtime (fetched 2026-03-11)
- https://assistant-ui.com/docs/runtimes/custom/local (fetched 2026-03-11)

## Open Questions

- The `RunConfig` type in `ChatModelRunOptions` - what fields does it contain? (likely model, temperature etc for future use)
- `ModelContext` fields - need to inspect if tools need to be explicitly forwarded to the backend
- Thread history persistence adapter - if AM needs conversation persistence across page refreshes, `ThreadHistoryAdapter` is the hook
