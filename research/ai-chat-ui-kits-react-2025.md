---
title: AI Chat UI Kits and Component Libraries for React (2025-2026)
type: research
tags: [react, ui, chat, streaming, components, shadcn, vercel, assistant-ui, prompt-kit]
summary: assistant-ui is the clear leader for production AI chat UI in React (8.8k stars, YC W25, streaming-first); prompt-kit is the best lightweight alternative for projects wanting shadcn-native composability without the full assistant-ui runtime.
status: active
source: deep-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

The React AI chat UI space consolidated sharply in 2025. **assistant-ui** is the dominant library: 8.8k stars, Y Combinator-backed, 50k+ monthly npm downloads, and the most complete production feature set (streaming, markdown, code highlighting, tool call rendering, message timing metadata, dark mode, keyboard shortcuts, voice). The only serious architectural competitor is the **Vercel AI Elements** collection (released August 2025), but it is intentionally shallower -- a set of copy-paste primitives rather than a cohesive runtime. For projects wanting a lighter-weight, shadcn-native component set without assistant-ui's runtime overhead, **prompt-kit** (by ibelick) is the best-maintained alternative. Everything else in this space is either dormant, AI-unaware, or a thin wrapper.

---

## Detailed Findings

### 1. assistant-ui

**GitHub:** https://github.com/assistant-ui/assistant-ui
**npm:** `@assistant-ui/react`
**Stars:** 8,800 (as of March 2026, up from near-zero at YC W25 batch start)
**Last commit:** March 9, 2026 (actively maintained, 1,166+ releases)
**Forks:** 914 | **Contributors:** 116
**License:** MIT
**Bundle size:** "Minimal" per docs; no Bundlephobia number confirmed -- the package uses modular ESM architecture with tree-shaking support. The core runtime has peer deps on React and shadcn/ui primitives.

**Architecture:** Radix-style composable primitives. You compose Thread, Composer, MessageList, and individual message part renderers rather than mounting a monolithic `<Chat>`. This is the key design distinction from every predecessor.

**Streaming support:** First-class and core to the architecture. Handles token-by-token rendering, auto-scroll during streaming, optimistic UI, and retries. Supports both SSE and WebSocket transports. Status enum (submitted / streaming / ready) is surfaced to components.

**Markdown + code highlighting:** Built-in. Shiki-based syntax highlighting. LaTeX via KaTeX. Mermaid diagram rendering. Diff viewer for code changes.

**Dark mode:** Yes, via shadcn/ui CSS variable theming system. Full light/dark switching.

**Keyboard shortcuts:** Yes, documented as a default capability. Cmd+Enter to submit, Escape to cancel -- follows platform conventions.

**Message metadata display:** Explicitly supported. Ships a "Message Timing" component that surfaces TTFT (time-to-first-token), total time, tokens/sec, and chunk count. Custom grouping functions let you organize message parts into flexible layouts -- this is the most direct answer to the "memory indicator / score / tag" requirement.

**Generative UI / tool calls:** Render tool calls and JSON as arbitrary React components inline. Collect human approvals inline (HITL pattern). Safe frontend actions.

**Backend agnosticism:** Works with Vercel AI SDK, LangGraph, Mastra, or any custom backend via a runtime adapter pattern. Does NOT require Vercel infrastructure.

**React Native:** Yes, officially supported.

**Notable gotchas:**
- Requires shadcn/ui initialization in your project (or manual Tailwind CSS variable setup). Not zero-config for a greenfield project without shadcn.
- Assistant Cloud (managed chat persistence + analytics) is a paid product from the same team. The core library is MIT/free, but the sales surface is visible.
- Bundle size is not published prominently -- the modular architecture means you pay only for what you import, but the runtime itself (state management, streaming, auto-scroll) does add weight beyond a bare component set.
- The library evolves fast (1,166+ releases). Minor APIs have shifted between minor versions.

**Community signal:** Adopted by LangChain, Stack AI, Browser Use, Athena Intelligence. SaaStr wrote a profile calling it "the React library eating the AI chat market." YC Winter 2025 batch. Discord community active.

---

### 2. Vercel AI Elements

**GitHub:** https://github.com/vercel/ai-elements
**Stars:** 1,700 (February 2026, growing post-launch)
**Last release:** ai-elements@1.8.4 (Feb 5, 2026)
**License:** MIT
**Released:** August 6, 2025

**Architecture:** Copy-paste component registry (same model as shadcn/ui itself). You run `npx ai-elements@latest`, select components, and they land in your `@/components/ai-elements/` directory. You own the code. No runtime dependency on a Vercel package beyond the AI SDK.

**Component inventory (20+):**
- Core chat: Conversation, Message, PromptInput, Response, Actions, Sources
- Reasoning/tools: Reasoning, Tool, Task, InlineCitation, Context
- Workflow (React Flow): Canvas, Node, Edge, Connection, Controls, Panel, Toolbar
- Coding artifacts: CodeBlock, Artifact, WebPreview, Image

**Streaming support:** Tightly integrated with `useChat()` from `@ai-sdk/react`. The `status === 'streaming'` state is handled by components. Backend uses `streamText()` + `toUIMessageStreamResponse()`. The coupling is intentional -- this is the Vercel AI SDK's own UI layer.

**Markdown + code:** CodeBlock component ships. Markdown rendering is handled inside the Response component. Syntax highlighting confirmed.

**Dark mode:** Not explicitly documented in README; inherits from shadcn/ui CSS variables.

**Keyboard shortcuts:** Not documented.

**Message metadata:** No dedicated metadata/timing display component observed.

**Gotchas:**
- Requires CSS Variables mode for Tailwind (not the older Tailwind class approach).
- Requires Next.js with AI SDK as the runtime. Not framework-agnostic -- this is a Vercel-stack component.
- Narrower scope than assistant-ui: no tool call rendering beyond display, no React Native, no non-Vercel backend adapters.
- "Replaces ChatSDK" per Vercel's own changelog -- ChatSDK is deprecated.
- 1.7k stars suggests strong initial interest but not the broad community that assistant-ui has built.

**When to choose:** You are already on Vercel + Next.js + AI SDK and want components that are literally part of that stack. Zero additional opinions needed. Copy-paste ownership means no versioning surprises.

---

### 3. prompt-kit (ibelick)

**GitHub:** https://github.com/ibelick/prompt-kit
**Stars:** 2,700+ (per March 2025 tracking; likely higher by March 2026)
**License:** MIT
**Author:** Julien Thibeaut (ibelick), active maintainer

**Architecture:** shadcn/ui copy-paste, installed via `npx shadcn@latest add prompt-kit/[component]`. 18 components across three tiers: Components (primitives), Blocks (composed UI pieces), and Primitives (full-stack blocks with Vercel AI SDK wiring).

**Full component list:** Chain of Thought, Chat Container, Code Block, Feedback Bar, File Upload, Image, Loader, Markdown, Message, Prompt Input, Prompt Suggestion, Reasoning, Scroll Button, Source, Steps, System Message, Text Shimmer, Thinking Bar, Tool.

**Streaming support:** "Streaming response UI" listed as a feature. Integrates with OpenAI SDK, Vercel AI SDK v5, and AI SDK-compatible backends. The Text Shimmer component is purpose-built for streaming animation.

**Markdown + code:** Dedicated Markdown component. Code Block uses Shiki with github-light/dark themes.

**Dark mode:** Yes. `dark:prose-invert` classes and CSS variable color scheme switching confirmed.

**Message metadata:** No dedicated metadata display component; would require custom composition.

**Gotchas:**
- Lighter runtime than assistant-ui -- no built-in auto-scroll state management, retry logic, or streaming transport. You bring the `useChat` hook and wire it yourself.
- Younger than assistant-ui (fewer battle-tested edge cases covered).
- The "Primitives" tier with full-stack wiring is newer and less documented.
- Stars grew from 340 (early March 2025) to 2,700+ -- the trajectory is strong but the library has not yet reached assistant-ui's breadth.

**When to choose:** You want high-quality shadcn-native components with no runtime lock-in, and you're comfortable wiring up the streaming state yourself (e.g., you already have a `useChat` integration or custom streaming).

---

### 4. shadcn-chatbot-kit (Blazity)

**GitHub:** https://github.com/Blazity/shadcn-chatbot-kit
**Stars:** 758
**License:** MIT

**Features:** Rich animations, file attachments, tool integration with visual states, Markdown with syntax highlighting, dark/light theme switching. Integrates with Vercel AI SDK.

**Streaming:** Wired through AI SDK's status tracking (submitted / streaming).

**WIP items:** "Thinking Process" visual block and "Voice Input" are marked WIP -- not production-ready.

**Verdict:** Nicely designed but narrow adoption and unfinished features. Not a safe primary choice for a production build.

---

### 5. shadcn-chat (jakobhoeg)

**GitHub:** https://github.com/jakobhoeg/shadcn-chat
**Stars:** 1,600
**Last commit:** January 5, 2025

**Critical finding:** The README explicitly states "I am no longer actively maintaining this library." Creator recommends alternatives. **Do not use** for new projects.

---

### 6. ChatScope (chat-ui-kit-react)

**GitHub:** https://github.com/chatscope/chat-ui-kit-react
**Stars:** 1,700
**Last commit:** May 15, 2025 (v2.1.1, React 19 peer dep update)
**Language:** 100% JavaScript

**Core problem for AI use:** ChatScope was built for human-to-human chat, not LLM streaming. There is **no native streaming support, no markdown rendering, and no code highlighting**. For LLM responses you would need to add react-markdown, a syntax highlighter, and build your own streaming renderer from scratch. The Message component accepts plain text only.

It is well-maintained for its original purpose (real-time human chat apps) but is **wrong-tool-for-job** for an AI chat interface in 2025.

---

### 7. llm-ui (richardgill)

**GitHub:** https://github.com/richardgill/llm-ui
**Stars:** ~1,700 (trending ~4.2 stars/day as of early 2025)

**Niche:** Headless streaming renderer focused specifically on the "flash of incomplete markdown" problem. Smooths out token delivery to native display frame rate. Shiki code blocks. Backend-agnostic.

**Gotcha:** Headless means you style everything. No opinionated UI -- just the rendering engine. Best used as a rendering primitive inside a larger UI, not as a standalone solution.

---

### 8. LlamaIndex chat-ui

**GitHub:** https://github.com/run-llama/chat-ui
**npm:** `@llamaindex/chat-ui`
**Stars:** 572
**Last release:** v0.6.1 (August 28, 2025)

**Features:** Tailwind-based, highlight.js + KaTeX for code and math, Vercel AI SDK integration, custom widgets for document/source display.

**Verdict:** Solid but narrow ecosystem fit (LlamaIndex users). Low stars relative to alternatives.

---

### 9. Vercel AI SDK useChat (not a UI library)

The `useChat` hook from `@ai-sdk/react` is the **state management layer**, not a UI library. It manages messages, streaming status, input state, and transport. Every library above (except ChatScope) sits on top of it or provides an adapter to it. Evaluating it as a "chat UI component library" is a category error -- it ships no rendered components in AI SDK 5.x (the Elements library is the UI layer, released separately).

---

## Streaming Markdown: The Core Technical Problem

A recurring HN discussion (item 44182941) identifies the "flash of incomplete markdown" as the primary streaming UX problem: incomplete markdown syntax renders incorrectly mid-stream (e.g., a `[text](` link that hasn't received its closing `)` yet).

Approaches observed across libraries:
- **assistant-ui:** Internal buffering with flush on newline; comprehensive battle-testing.
- **AI Elements:** Response component handles it internally.
- **prompt-kit:** Markdown component listed but streaming buffering not documented -- likely consumer's responsibility to integrate with llm-ui or react-markdown's streaming mode.
- **llm-ui:** Dedicated solution to this specific problem; "removes broken markdown syntax" and renders at native frame rate.
- **ChatScope:** Does not address this; consumer responsibility.

---

## Sources Consulted

### GitHub repositories
- [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) -- 8.8k stars
- [vercel/ai-elements](https://github.com/vercel/ai-elements) -- 1.7k stars
- [ibelick/prompt-kit](https://github.com/ibelick/prompt-kit) -- 2.7k stars
- [Blazity/shadcn-chatbot-kit](https://github.com/Blazity/shadcn-chatbot-kit) -- 758 stars
- [jakobhoeg/shadcn-chat](https://github.com/jakobhoeg/shadcn-chat) -- 1.6k stars (ABANDONED)
- [chatscope/chat-ui-kit-react](https://github.com/chatscope/chat-ui-kit-react) -- 1.7k stars
- [richardgill/llm-ui](https://github.com/richardgill/llm-ui)
- [run-llama/chat-ui](https://github.com/run-llama/chat-ui) -- 572 stars

### Official documentation and changelogs
- [Vercel AI Elements changelog](https://vercel.com/changelog/introducing-ai-elements)
- [AI SDK v5 announcement](https://vercel.com/blog/ai-sdk-5)
- [AI SDK v6 announcement](https://vercel.com/blog/ai-sdk-6)
- [assistant-ui.com](https://www.assistant-ui.com/)
- [prompt-kit.com](https://www.prompt-kit.com/)

### Articles and analysis
- [LogRocket: Building with Vercel AI Elements](https://blog.logrocket.com/vercel-ai-elements/)
- [InfoQ: Vercel Releases AI Elements Library](https://www.infoq.com/news/2025/08/vercel-ai-sdk/)
- [YC company page: assistant-ui](https://www.ycombinator.com/companies/assistant-ui)

### HackerNews discussions
- [Flash of incomplete markdown when streaming](https://news.ycombinator.com/item?id=44182941)
- [Practical approach for streaming UI from LLMs](https://news.ycombinator.com/item?id=44955612)

---

## Source Quality Assessment

**Confidence: High** for the top-tier findings (assistant-ui vs AI Elements positioning, star counts, feature inventory). The GitHub data is current as of the session date (March 9, 2026). The SaaStr article on assistant-ui was not parseable (WordPress CSS bloat), but corroborating data (YC, star count, npm downloads, named adopters) is triangulated from multiple independent sources. ChatScope's limitations were confirmed directly from its README. prompt-kit's streaming approach is partially inferred from its component inventory and Vercel AI SDK compatibility claim -- the exact internal buffering implementation was not verified.

**Gap:** No first-person developer experience data from Reddit or X threads was retrievable (site: searches returned no results for this specific topic). The star counts for prompt-kit have likely grown since the 340-star figure from early March 2025 -- the 2.7k figure comes from the GitHub repository fetch.

---

## Open Questions

1. What is the actual gzipped bundle size of `@assistant-ui/react` in a minimal configuration? Bundlephobia was rate-limited during this session.
2. Does prompt-kit's Markdown component handle the streaming flash-of-incomplete-markdown problem internally, or does it delegate that to the consumer?
3. How does assistant-ui's thread branching/message editing interact with a custom backend (non-Vercel)?
4. Are there X/Twitter practitioners who have compared AI Elements and assistant-ui in production? The social signal was not accessible via search.
5. What is the Vercel AI Elements roadmap for non-Next.js support?

---

## Actionable Takeaways

### Top-2 Recommendations

**Recommendation 1: assistant-ui** -- Use this for any production AI chat interface where you want the complete, battle-tested solution.

Rationale:
- The only library in this space with a first-class runtime: streaming transport, auto-scroll, retry, HITL, tool call rendering, and message timing metadata are all built in.
- The composable primitives model means you are not fighting a monolithic `<Chat>` component when your design diverges from defaults.
- Message Timing component (TTFT, tok/s, chunk count) directly addresses the "memory indicators / scores / tags" requirement -- you compose your custom metadata display in the same slot.
- 8.8k stars + YC + named enterprise adopters means the dependency is safe to take.
- Works with any backend; you do not need Vercel infrastructure.
- The main cost: you need shadcn/ui initialized, and you accept a runtime dependency (not just copy-paste components).

**Recommendation 2: prompt-kit + Vercel AI SDK useChat** -- Use this when you want shadcn-native components without a runtime dependency, and you are already wiring `useChat` yourself.

Rationale:
- True copy-paste ownership: no versioning surprises, no runtime.
- 18 well-designed components covering the full AI chat surface (Reasoning, Chain of Thought, Thinking Bar, Tool, Source, Feedback Bar -- all purpose-built for 2025-era LLM UX patterns).
- Shiki code highlighting with github-light/dark, dedicated dark mode, MIT license.
- The tradeoff: you own the streaming state management. If you're building on Vercel AI SDK's `useChat`, this is not a burden -- the hook handles it. But if you need auto-scroll, retry, and thread persistence, you build that layer yourself.

### What to avoid
- **shadcn-chat (jakobhoeg):** Abandoned, maintainer explicitly says so.
- **ChatScope:** Not built for LLM output. Wrong tool.
- **Vercel AI Elements** as a standalone choice: Only makes sense if you are 100% committed to the Vercel/Next.js/AI SDK stack. The 1.7k star count and shallow feature set (vs. assistant-ui) suggest it has not yet earned a first-choice position outside that ecosystem.

### Suggested follow-up
- Benchmark assistant-ui bundle via Bundlephobia once rate limit clears.
- Check assistant-ui's `Composer.Attachments` and custom `MessagePrimitive` slots for the memory indicator / score display pattern needed in the attention-matters UI.
- Evaluate llm-ui as a rendering primitive if streaming markdown flicker becomes a problem with the chosen library.
