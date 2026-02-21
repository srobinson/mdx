---
title: AI Chat UI Streaming Libraries Landscape 2025
type: research
tags: [ai-chat, streaming, react, frontend, ui-libraries, open-webui, librechat, lobechat, assistant-ui, vercel-ai-sdk, ag-ui, copilotkit]
summary: assistant-ui is the clear winner for React component library use; pair it with Streamdown for markdown. For full-application forks, LibreChat is the most embeddable. Vercel AI SDK is the universal streaming primitive. AG-UI is the emerging open protocol that will reshape this space.
status: active
source: deep-research
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Executive Summary

The 2025-2026 AI chat UI landscape has stratified cleanly into three layers: streaming primitives (Vercel AI SDK, AG-UI protocol), component libraries (assistant-ui dominant, prompt-kit second), and full application forks (LibreChat, Open WebUI, LobeChat). For a custom Rust backend that emits SSE, the clearest path is: **assistant-ui** as the component layer, **Vercel AI SDK useChat** as the streaming state hook (pointed at your own SSE endpoint), and **Streamdown** (vercel/streamdown) for streaming markdown. This stack requires zero OpenAI dependency and works with any backend that speaks text/event-stream. The Thoughtworks Tech Radar (2026) placed assistant-ui in the "Assess" ring -- institutional validation from a conservative evaluator.

---

## Detailed Findings

### Category 1: Streaming Primitives

#### Vercel AI SDK (ai / @ai-sdk/react)

**What it is:** The de facto standard state management and transport layer for AI chat in React, Vue, Svelte, and Angular. Not a UI library -- it ships no rendered components. It is the hook and protocol layer that every major chat UI library plugs into.

**Custom backend story:** Fully supported. Two stream protocols:
- **Text stream protocol** (`streamProtocol: 'text'`): Your backend emits plain text chunks. Zero infrastructure requirements. The simplest possible integration.
- **Data stream protocol** (default): Your backend emits SSE with structured JSON parts (message start/delta/end, tool calls, etc.) and the `x-vercel-ai-ui-message-stream: v1` header. Enables tool calls, reasoning blocks, and custom data.

The SDK also ships an `openai-compatible` provider adapter -- if your Rust backend implements the OpenAI chat completions streaming format, you get full AI SDK compatibility with no custom protocol work.

**AI SDK 5 changes (major):** Separate UIMessages (frontend state) and ModelMessages (LLM wire format). Framework-agnostic: Vue, Svelte, Angular now have full feature parity. `AbstractChat` class exposed for custom hook building. Flexible transport layer -- swap fetch for WebSockets.

**AI SDK 6 status (current):** Introduced `Agent` abstraction with `ToolLoopAgent`. MCP support marked stable. New debugging tools. `rerank` function. The v3 Language Model Specification is the headline, but most users see minimal breaking changes.

**Stars (vercel/ai):** 35k+. npm `ai` package: industry-leading weekly downloads. The `@ai-sdk/react` package has 257+ dependent npm packages.

**Bottom line:** Use the text stream protocol for a Rust backend. Three lines of server code (emit `data: <chunk>\n\n`), one hook call on the client. This is not optional infrastructure -- it is the layer every other library assumes.

---

#### AG-UI Protocol

**What it is:** An open, event-based streaming protocol for agent-user interaction. Announced May 2025 by the CopilotKit team. 12.4k GitHub stars in under a year.

**How it works:** Standardizes event types for streaming between agents and frontends over SSE, WebSockets, or webhooks. Events cover: text streaming, tool call streaming, state synchronization, human-in-the-loop approval, and custom events.

**Backend support:** LangGraph, CrewAI, Pydantic AI, Mastra, Google ADK, AWS Strands, LlamaIndex, AG2. Vercel AI SDK integration is in progress.

**Frontend support:** CopilotKit is the primary client. TanStack AI implements the AG-UI protocol for streaming.

**Why it matters for custom backends:** If you implement AG-UI events in your Rust backend, you get CopilotKit and TanStack AI frontend support for free. The protocol is lightweight -- less prescriptive than the Vercel AI SDK data stream format.

**Status:** Emerging, not yet the dominant protocol. Vercel AI SDK data stream is still the most widely implemented format. Watch this space for 2026-2027.

---

#### TanStack AI (@tanstack/ai-react)

**What it is:** Alpha-stage React AI library from the TanStack team (creators of React Query, React Table, TanStack Router). Announced late 2025.

**Architecture:** Uses AG-UI protocol for streaming. `useChat` hook managing messages, loading states, and server communication. Type-safe tool calling. Provider-agnostic (OpenAI, Anthropic, Gemini, Ollama, OpenRouter).

**Status:** Alpha. Given TanStack's track record of shipping high-quality, framework-agnostic primitives (React Query is the gold standard), this is worth tracking. Not ready for production today.

---

### Category 2: React Component Libraries

#### assistant-ui (RECOMMENDED)

**GitHub:** https://github.com/assistant-ui/assistant-ui
**npm:** `@assistant-ui/react`
**Stars:** 8.8k (March 2026)
**Last commit:** March 10, 2026 (Release @assistant-ui/react@0.12.17 -- actively maintained)
**Forks:** 916 | **Dependents:** 2.3k npm packages | **Releases:** 1,172+
**License:** MIT
**Backing:** Y Combinator W25, SaaStr Fund

**Architecture:** Radix-style composable primitives. You compose `Thread`, `Composer`, `MessageList`, and individual message part renderers rather than mounting a monolithic `<Chat>`. This is the key design distinction from every predecessor library.

**Streaming:** First-class and core to the architecture. Token-by-token rendering, auto-scroll during streaming, optimistic UI, retries. Supports both SSE and WebSocket transports. Status enum (submitted / streaming / ready) surfaced to all components.

**Markdown + code highlighting:** Built-in. Shiki-based syntax highlighting. LaTeX via KaTeX. Mermaid diagram rendering. Diff viewer for code changes.

**Custom backend story:** The `LocalRuntime` adapter is the key. Implement a single `ChatModelAdapter.run()` method that calls your backend -- no protocol prescribed. Returns a plain async generator of text chunks. Works with any REST endpoint, any streaming format, OpenAI-compatible or not. Setup is approximately 30 lines of TypeScript.

```typescript
const CustomAPIAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const response = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ messages }),
      signal: abortSignal,
    });
    // read SSE or chunked body here, yield text chunks
    for await (const chunk of parseSSE(response.body)) {
      yield { content: [{ type: "text", text: chunk }] };
    }
  }
};
```

**Tool call rendering:** Renders tool calls and JSON as arbitrary React components inline. HITL (human-in-the-loop) approval pattern built in.

**Metadata display:** Ships a `MessageTiming` component surfacing TTFT, total time, tokens/sec, and chunk count. Custom metadata composable via message part slots.

**React Native:** Officially supported.

**Thoughtworks Tech Radar:** "Assess" ring (2026). Thoughtworks notes: "We've successfully built a simple chat interface with assistant-ui and have been pleased with the results." This is significant -- Thoughtworks is conservative and slow to recommend.

**Community traction:** Adopted by LangChain, Stack AI, Browser Use, Athena Intelligence, Mastra, Iterable. 200k+ monthly npm downloads (per SaaStr profile). Discord active. Named in SaaStr "AI App of the Week."

**Gotchas:**
- Requires shadcn/ui initialization (or manual Tailwind CSS variable setup). Not zero-config without shadcn.
- The library evolves fast (1,172+ releases). Minor APIs have shifted between versions -- pin carefully.
- Assistant Cloud (managed persistence + analytics) is a paid upsell. Core library is MIT/free.
- Bundle size is modular (ESM with tree-shaking) but the runtime adds real weight beyond a bare component set.

---

#### Vercel AI Elements

**GitHub:** https://github.com/vercel/ai-elements
**Stars:** 1.7k (growing post-Aug 2025 launch)
**License:** MIT
**Released:** August 6, 2025

**Architecture:** Copy-paste component registry (same model as shadcn/ui). Run `npx ai-elements@latest`, pick components, they land in your codebase. You own the code -- no runtime dependency.

**20+ components:** Conversation, Message, PromptInput, Response, Actions, Sources, Reasoning, Tool, Task, InlineCitation, CodeBlock, Artifact, WebPreview, Canvas (React Flow), and more.

**Streaming:** Tightly coupled to `useChat()` from `@ai-sdk/react`. Works exclusively within the Vercel AI SDK stack.

**Custom backend story:** Backend must speak the Vercel AI SDK data stream protocol. Not easily pointed at an arbitrary Rust backend without implementing the protocol on the server side.

**When to choose:** You are on Vercel + Next.js + AI SDK and want zero-opinion components from the same team. Do not choose if you need backend flexibility.

---

#### prompt-kit (ibelick)

**GitHub:** https://github.com/ibelick/prompt-kit
**Stars:** 2.7k+ (strong upward trajectory)
**License:** MIT

**Architecture:** shadcn/ui copy-paste. 18 components: Chain of Thought, Chat Container, Code Block, Feedback Bar, File Upload, Loader, Markdown, Message, Prompt Input, Prompt Suggestion, Reasoning, Scroll Button, Source, Steps, System Message, Text Shimmer, Thinking Bar, Tool.

**Streaming:** "Streaming response UI" listed as a feature. Integrates with Vercel AI SDK v5. Text Shimmer component purpose-built for streaming animation.

**Custom backend story:** You bring `useChat` and wire it yourself. The components are rendering primitives -- they do not prescribe transport. More flexible than AI Elements for non-Vercel stacks.

**Gotchas:** Lighter runtime than assistant-ui -- no built-in auto-scroll state management, retry logic, or streaming transport. You own that layer.

**When to choose:** High-quality shadcn-native components without runtime lock-in. Already comfortable wiring `useChat` or a custom streaming hook yourself.

---

#### LlamaIndex chat-ui (@llamaindex/chat-ui)

**GitHub:** https://github.com/run-llama/chat-ui
**npm:** `@llamaindex/chat-ui`
**Stars:** 572 | **Last release:** v0.6.1 (August 28, 2025) | **License:** MIT

Pre-built Tailwind chat components. highlight.js + KaTeX for code and math. Integrates with Vercel AI SDK. Built for LlamaIndex users. Low community size relative to alternatives. Skip unless you are already on the LlamaIndex stack.

---

#### react-chatbotify

**GitHub:** https://github.com/react-chatbotify/react-chatbotify (tjtanjin/react-chatbotify)
**Stars:** 436 | **Last release:** v2.5.0 (Nov 18, 2025) | **License:** MIT

Streaming support via LLM connector plugin. Compatible with React 16-19. Plugin architecture for extensibility. Flow-based conversation design (chatbot-style state machines). Positioned for flow-based chatbots more than open-ended AI chat. Much smaller community than assistant-ui. Not the right fit for an open-ended streaming chat interface.

---

#### ChatScope (chat-ui-kit-react)

**GitHub:** https://github.com/chatscope/chat-ui-kit-react
**Stars:** 1.7k | **Last commit:** May 15, 2025 (React 19 peer dep update) | **Language:** JavaScript

Built for human-to-human chat, not LLM streaming. No native streaming support, no markdown rendering, no code highlighting. Wrong tool for an AI chat interface in 2025. 32k weekly downloads reflects legacy projects, not new adoption.

---

### Category 3: Streaming Markdown Libraries

#### Streamdown (vercel/streamdown) -- RECOMMENDED

**GitHub:** https://github.com/vercel/streamdown
**Stars:** 4.7k | **Created:** August 2025 | **Dependents:** ~1,900 | **Latest:** @streamdown/code@1.1.0 (March 2026)

A drop-in replacement for react-markdown, purpose-built for streaming AI output. Solves the "flash of incomplete markdown" problem: unterminated bold, open code fences, unclosed links all render correctly during streaming without flickering.

**Key features:**
- Incomplete syntax rendered correctly mid-stream (unterminated code blocks styled as code immediately)
- GitHub Flavored Markdown (tables, task lists, strikethrough)
- Math via KaTeX, diagrams via Mermaid
- Code syntax highlighting via Shiki
- Accepts same props as react-markdown (remarkPlugins, rehypePlugins)
- Security-focused via rehype-harden
- Memoized rendering for performance

**Production readiness:** 44 releases, 1,900 dependents, active maintenance through March 2026. Vercel-authored -- same team as the AI SDK.

---

#### llm-ui (richardgill)

**GitHub:** https://github.com/richardgill/llm-ui
**Stars:** ~1.7k

Headless streaming renderer focused on the same incomplete-markdown problem. Removes broken markdown syntax, renders at native frame rate. Shiki code blocks. Backend-agnostic. Useful as a rendering primitive inside a larger UI, but you style everything yourself. Streamdown is the better default in 2025 unless you need headless control.

---

### Category 4: Full Application Forks

These are complete self-hosted applications you fork and customize -- not component libraries. Use these when you want a working chat product quickly, not when you are embedding chat into an existing app.

#### LibreChat

**GitHub:** https://github.com/danny-avila/LibreChat
**Stars:** 34.5k | **Forks:** 7k | **Frontend stack:** React + TypeScript (70%) + JavaScript (28%)
**License:** MIT

The most backend-flexible full chat application. Custom endpoints configured via `librechat.yaml` -- any OpenAI-compatible API works with no proxy required. If your Rust backend exposes an OpenAI-compatible `/v1/chat/completions` endpoint (relatively simple to implement with axum or actix-web), LibreChat connects to it with three lines of YAML config.

**Frontend:** React-based (`/client` directory). Modifiable. 3,836 commits. 241 open issues, 204 open PRs -- actively developed, not stagnant.

**MCP support:** Yes (listed in the feature description).

**Multi-user:** Built-in secure multi-user auth. Important for production deployments.

**Custom backend difficulty:** Low-to-medium. Requires implementing the OpenAI streaming response format on your Rust backend (well-documented, multiple Rust crates available). Then it is YAML configuration.

**When to use:** You want a production-grade chat application with conversation history, multi-user auth, and a polished UI in days, not weeks. You are willing to implement OpenAI wire format compatibility on your Rust backend.

---

#### Open WebUI

**GitHub:** https://github.com/open-webui/open-webui
**Stars:** 127k | **Frontend stack:** Svelte + TypeScript + Tailwind + Vite

The most-starred open source chat frontend by a wide margin. Originally built for Ollama, expanded to support any OpenAI-compatible API.

**Frontend:** Svelte (not React). Not embeddable as a component library -- it is a self-contained application deployed via Docker or pip. Not the right choice if you need to embed chat into an existing React app.

**Custom backend:** Requires OpenAI-compatible API surface or a Python Pipeline adapter. Pipelines are powerful (Python-based middleware) but add deployment complexity.

**Community:** 347k users, 290M downloads. The largest community in this space.

**When to use:** You are running Ollama or an OpenAI-compatible local model and want a mature, full-featured self-hosted UI. Not the right fit for embedding into an existing web app or if your stack is React-only.

---

#### LobeChat (lobehub/lobe-chat)

**GitHub:** https://github.com/lobehub/lobe-chat (via lobehub org)
**Stars:** 73.4k | **Frontend stack:** React + TypeScript + Next.js

The most visually polished of the full chat applications. Multi-provider support (OpenAI, Claude, Gemini, Ollama, DeepSeek, Qwen). Knowledge base with RAG. Plugin system. Voice chat. Mobile support.

**Custom backend:** Supports multiple AI providers including local LLMs via Ollama. An issue (#9569) documents friction around embedding-provider flexibility -- not all customization points are clean.

**Embeddability:** Not designed as a component library. Full Next.js application. LobeHub publishes a separate `lobe-ui` component library but it is oriented toward their own ecosystem.

**When to use:** You want the best-looking chat application and are willing to deploy it as a standalone service. Not for embedding into an existing app.

---

#### CopilotKit

**GitHub:** https://github.com/CopilotKit/CopilotKit
**Stars:** 26k | **License:** MIT (with optional managed cloud)
**Stack:** React + Next.js + Angular SDKs

Positioned as "The Frontend for Agents & Generative UI." Not a chat-only library -- it is a full agentic application framework. The AG-UI protocol originated from this team.

**Custom backend:** `@copilotkit/runtime` is a self-hostable server-side middle layer. Connects to LangGraph agents, Python-based backends, or direct LLM providers.

**Streaming:** AG-UI protocol, streaming-first. `useAgent` hook (v1.50) is the primary entry point.

**When to use:** You are building an agentic application with tool use, HITL workflows, and state synchronization -- not just a simple chat interface. CopilotKit is heavier-weight than assistant-ui but more powerful for agent-driven UI patterns.

---

#### Chainlit (Python)

Not a React library. Python framework that provides a production-quality chat UI with SSE streaming, file upload, user sessions, and WebSocket management -- all in Python. Renders its own React-based frontend. Useful for Python ML backends, not for embedding into a React application or connecting to a Rust backend.

---

## Sources Consulted

### GitHub repositories (verified March 2026)
- [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) -- 8.8k stars
- [vercel/streamdown](https://github.com/vercel/streamdown) -- 4.7k stars
- [danny-avila/LibreChat](https://github.com/danny-avila/LibreChat) -- 34.5k stars
- [open-webui/open-webui](https://github.com/open-webui/open-webui) -- 127k stars
- [lobehub/lobe-chat](https://github.com/lobehub/lobe-chat) -- 73.4k stars
- [CopilotKit/CopilotKit](https://github.com/CopilotKit/CopilotKit) -- 26k stars
- [ag-ui-protocol/ag-ui](https://github.com/ag-ui-protocol/ag-ui) -- 12.4k stars
- [TanStack/ai](https://github.com/TanStack/ai)
- [ibelick/prompt-kit](https://github.com/ibelick/prompt-kit) -- 2.7k stars
- [Blazity/shadcn-chatbot-kit](https://github.com/Blazity/shadcn-chatbot-kit) -- 761 stars
- [run-llama/chat-ui](https://github.com/run-llama/chat-ui) -- 572 stars
- [react-chatbotify/react-chatbotify](https://github.com/react-chatbotify/react-chatbotify) -- 436 stars
- [chatscope/chat-ui-kit-react](https://github.com/chatscope/chat-ui-kit-react) -- 1.7k stars

### Official documentation
- [assistant-ui LocalRuntime docs](https://www.assistant-ui.com/docs/runtimes/custom/local)
- [Vercel AI SDK stream protocols](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol)
- [AI SDK 5 announcement](https://vercel.com/blog/ai-sdk-5)
- [AI SDK 6 announcement](https://vercel.com/blog/ai-sdk-6)
- [AG-UI protocol docs](https://docs.ag-ui.com/)
- [Open WebUI custom backend docs](https://docs.openwebui.com/tutorials/integrations/backend-controlled-ui-compatible-flow/)
- [LibreChat custom endpoints](https://www.librechat.ai/docs/quick_start/custom_endpoints)
- [TanStack AI docs](https://tanstack.com/ai/latest/docs)
- [Streamdown docs](https://streamdown.ai/docs)

### Industry analysis
- [Thoughtworks Tech Radar -- assistant-ui ("Assess" ring, 2026)](https://www.thoughtworks.com/en-us/radar/languages-and-frameworks/assistant-ui)
- [Builder.io -- React + AI Stack for 2026](https://www.builder.io/blog/react-ai-stack-2026)
- [Portkey -- LibreChat vs Open WebUI](https://portkey.ai/blog/librechat-vs-openwebui/)
- [Elest.io -- LobeChat vs Open WebUI vs LibreChat](https://blog.elest.io/the-best-open-source-chatgpt-interfaces-lobechat-vs-open-webui-vs-librechat/)

### HackerNews discussions
- [Assistant-UI: React components for AI chat](https://news.ycombinator.com/item?id=41684292) -- cautious optimism, question about custom backend support
- [Show HN: A React and Next.js UI Toolkit for LLMs](https://news.ycombinator.com/item?id=40658605)
- [Show HN: Tambo -- React toolkit for AI-powered UIs](https://news.ycombinator.com/item?id=43556664)
- [Practical approach for streaming UI from LLMs](https://news.ycombinator.com/item?id=44955612)

---

## Source Quality Assessment

**Confidence: High** for layer-1 findings (library stars, feature inventories, custom backend protocols). GitHub data is current as of March 11, 2026. Stream protocol behavior for Vercel AI SDK was verified against official documentation. Streamdown stars and dependent counts verified directly from the repository.

**Confidence: Medium** for community sentiment. Reddit `site:` searches returned no results across multiple query formulations -- the AI chat UI topic is fragmented across subreddits and Discord servers rather than concentrated in indexed Reddit threads. The Thoughtworks Radar placement and Builder.io analysis provide institutional community signal as proxies.

**Gaps:**
- No first-person Reddit or X practitioner comparisons verified. Community consensus is inferred from star trajectories, npm downloads, and institutional signals (YC, Thoughtworks).
- TanStack AI is alpha -- feature set and stability unverified in production.
- AG-UI protocol's Vercel AI SDK integration is "in progress" -- timeline unknown.
- Bundle size comparisons were not benchmarked directly.

---

## Open Questions

1. What is the gzipped bundle size of `@assistant-ui/react` in a minimal LocalRuntime configuration?
2. Does Streamdown's incomplete-markdown handling compose cleanly inside assistant-ui's message renderer, or does assistant-ui's internal markdown handling conflict?
3. When will AG-UI's Vercel AI SDK integration ship? That would unify the two dominant streaming primitives.
4. For a Rust backend: what is the minimal Axum/Actix implementation needed to emit the Vercel AI SDK text stream protocol? (One SSE endpoint emitting `data: <chunk>\n\n` should suffice.)
5. Does LibreChat's React client cleanly separate from its Node.js backend, making the frontend forkable without the full LibreChat server?

---

## Actionable Takeaways

### For embedding chat into an existing React app (talking to a custom Rust backend)

This is the primary use case. The recommended stack:

**1. Vercel AI SDK `useChat` (transport layer)**

Use `streamProtocol: 'text'` to point at your Rust backend. Your Rust backend emits `data: <chunk>\n\n` over SSE -- that is the entire server-side requirement. No OpenAI compatibility needed.

```typescript
const { messages, input, handleSubmit } = useChat({
  api: "/your-rust-endpoint",
  streamProtocol: "text",
});
```

**2. assistant-ui (component layer)**

Use the `LocalRuntime` adapter wrapping your `fetch` call. assistant-ui takes over message state, auto-scroll, retry, and all rendering. You connect it to the AI SDK or write a direct adapter -- either works.

**3. Streamdown (markdown rendering)**

Drop Streamdown in as the markdown renderer inside assistant-ui's message content renderer. It handles all incomplete-markdown edge cases during streaming.

This stack is backend-agnostic, requires no Vercel infrastructure, and gives you a production-quality chat UI in a day.

---

### For shipping a standalone chat application fast

**Fork LibreChat.** It has 34.5k stars, active maintenance, React frontend, multi-user auth, conversation history, and requires only an OpenAI-compatible endpoint from your backend. Implementing `POST /v1/chat/completions` with streaming in axum or actix-web is a day of work. You get a production-grade frontend immediately.

---

### What to skip

| Library | Why |
|---|---|
| Open WebUI | Svelte, not React. Application-only, not embeddable. |
| ChatScope | Built for human-to-human chat. No LLM streaming or markdown. |
| shadcn-chat (jakobhoeg) | Abandoned. Maintainer explicitly warns against use. |
| react-chatbotify | Flow-based chatbot design, not open-ended LLM chat. |
| Chainlit | Python-only. Wrong stack for a Rust + React project. |
| Gradio / Streamlit | Python rapid-prototyping tools. Not production React UI. |
| TanStack AI | Alpha. Not ready for production. Track for 2026. |

---

### Watch list (not ready today, important by late 2026)

- **TanStack AI:** If it reaches stable with the TanStack team's track record, it will be the most rigorous type-safe option. The AG-UI protocol integration gives it a clean streaming story.
- **AG-UI protocol:** Gaining momentum. If your Rust backend implements AG-UI events, you get CopilotKit + TanStack AI + future frontends for free. The protocol is simple enough to implement in a few hundred lines.
- **Vercel AI Elements:** 20+ copy-paste components from the AI SDK team. Not yet framework-agnostic, but if they decouple from Next.js, this becomes a strong second choice to prompt-kit.
