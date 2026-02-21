---
title: ALP-1127 Chat Interface Tech Stack Validation
type: research
tags: [assistant-ui, streamdown, axum, reqwest, openrouter, sse, react]
summary: All 4 stack assumptions validated - clean composition, correct patterns confirmed, reqwest needs eventsource-stream crate
status: active
source: quick-research
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

All 4 tech stack assumptions for the ALP-1127 chat interface are valid. Key finding: `@assistant-ui/react-streamdown` is a first-party package that replaces (not augments) `@assistant-ui/react-markdown`. Use `eventsource-stream` with reqwest to handle OpenRouter SSE correctly.

## Details

### Q1 - @streamdown/react inside assistant-ui

**Result: clean composition, no conflict.**

`@assistant-ui/react-streamdown` is an official first-party package from the assistant-ui team. It slots in as a drop-in replacement for `@assistant-ui/react-markdown` - not a layer on top of it:

```tsx
<MessagePrimitive.Parts components={{ Text: StreamdownText }} />
```

The two packages are mutually exclusive alternatives. No conflict risk. Streamdown ships with Shiki syntax highlighting, KaTeX math, and Mermaid support built in. Tradeoff is bundle size.

**Do not install `@assistant-ui/react-markdown` alongside it.**

Ref: https://www.assistant-ui.com/docs/ui/streamdown

---

### Q2 - axum 0.8 SSE pattern

**Use `axum::response::sse::Sse` - no manual chunked transfer needed.**

Confirmed against docs.rs/axum 0.8.8:

```rust
use axum::response::sse::{Event, KeepAlive, Sse};
use futures_util::stream::{self, Stream};
use std::{convert::Infallible, time::Duration};

async fn sse_handler() -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let stream = stream::repeat_with(|| Event::default().data("hi!"))
        .map(Ok)
        .throttle(Duration::from_secs(1));

    Sse::new(stream).keep_alive(KeepAlive::default())
}
```

For dynamic streaming from a channel, use `async-stream`'s `try_stream!` macro and yield events from the receiver. axum automatically sets `Content-Type: text/event-stream` and `Cache-Control: no-cache`.

Cargo deps:
```toml
axum = "0.8"
tokio = { version = "1", features = ["full"] }
futures-util = "0.3"
tokio-stream = { version = "0.1", features = ["time"] }
```

Note: as of 0.8.5, the SSE module no longer requires the tokio feature for basic use (only for keep-alive).

Ref: https://docs.rs/axum/latest/axum/response/sse/

---

### Q3 - reqwest stream feature + OpenRouter SSE

**reqwest handles it correctly; use `eventsource-stream` for parsing.**

OpenRouter SSE format is standard: `data: {...}\n\n` with `data: [DONE]` terminator and occasional comment lines (`: OPENROUTER PROCESSING`) that must be ignored per SSE spec.

reqwest's `bytes_stream()` delivers raw byte chunks that may split across SSE line boundaries. Hand-rolling `"data: "` parsing is fragile. Use `eventsource-stream`:

```rust
use eventsource_stream::Eventsource;
use futures_util::StreamExt;

let mut stream = client
    .post("https://openrouter.ai/api/v1/chat/completions")
    .json(&body)
    .send()
    .await?
    .bytes_stream()
    .eventsource();

while let Some(event) = stream.next().await {
    match event {
        Ok(ev) if ev.data == "[DONE]" => break,
        Ok(ev) => { /* parse ev.data as JSON chunk */ }
        Err(e) => return Err(e.into()),
    }
}
```

`eventsource-stream` handles partial chunks and multi-byte character splits internally (uses `nom` for parsing). No known buffering issues with OpenRouter specifically.

Cargo deps:
```toml
eventsource-stream = "0.2"
reqwest = { version = "0.12", features = ["stream", "json"] }
```

Ref: https://lib.rs/crates/eventsource-stream

---

### Q4 - Minimal ChatModelAdapter.run() for plain text SSE

**Use async generator (`async *run`) reading raw body chunks.**

The official LocalRuntime pattern for plain text SSE (no SDK, no protocol wrapping):

```typescript
import { ChatModelAdapter, ChatModelRunOptions } from "@assistant-ui/react";

const MyModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }: ChatModelRunOptions) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal: abortSignal,
    });

    if (!response.ok) throw new Error(response.statusText);

    let text = "";
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        // Strip SSE framing: "data: ...\n"
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (line.startsWith("data: ") && line !== "data: [DONE]") {
            text += line.slice(6);
          }
        }
        yield { content: [{ type: "text", text }] };
      }
    } finally {
      reader.releaseLock();
    }
  },
};
```

Key invariants:
- `text` accumulates outside the loop - assistant-ui replaces content on each yield, so you must yield the full accumulated string each time
- Use `{ stream: true }` in `TextDecoder.decode()` to handle multi-byte chars split across chunks
- `abortSignal` is passed through automatically from stop-generation UI
- Tool call accumulation has the same requirement - state must live outside the loop

Wire to LocalRuntime:
```tsx
const runtime = useLocalRuntime(MyModelAdapter);
<AssistantRuntimeProvider runtime={runtime}>...</AssistantRuntimeProvider>
```

Ref: https://www.assistant-ui.com/docs/runtimes/custom/local

---

## Sources

- https://www.assistant-ui.com/docs/ui/streamdown
- https://docs.rs/axum/latest/axum/response/sse/
- https://lib.rs/crates/eventsource-stream
- https://openrouter.ai/docs/api/reference/streaming
- https://www.assistant-ui.com/docs/runtimes/custom/local

## Open Questions

- ALP-1135 / ALP-1136 Linear comments could not be posted (Linear MCP token expired at time of research). Findings saved here instead.
- Whether to use `streamProtocol: 'text'` with Vercel AI SDK `useChat` vs the manual fetch approach in Q4 - the two paths are alternatives. If using useChat, the backend must speak the AI SDK stream protocol, not raw SSE.
